"""
CRM Service - Lead Management API with External CRM Sync & Email.
Provides endpoints for creating, reading, managing leads, and syncing them
to external CRM providers (HubSpot / Salesforce) via the Adapter Pattern.
"""
import os
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session
import logging

from .database import engine, get_db, Base
from .models import Lead, LeadStatus
from .schemas import LeadCreate, LeadResponse, LeadUpdate, EmailRequest, SyncResponse
from .email_service import send_email, send_lead_notification
from .adapters.base import CRMClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# CRM Adapter Factory
# =============================================================================

_crm_client = None  # Singleton


def get_crm_client() -> CRMClient | None:
    """
    Factory function that creates the appropriate CRM adapter
    based on the CRM_PROVIDER environment variable.
    Returns None if provider is 'none' or not configured.
    """
    global _crm_client
    if _crm_client is not None:
        return _crm_client

    provider = os.getenv("CRM_PROVIDER", "none").lower()

    if provider == "hubspot":
        try:
            from .adapters.hubspot_client import HubSpotAdapter
            _crm_client = HubSpotAdapter()
            return _crm_client
        except Exception as e:
            logger.error(f"❌ Failed to init HubSpot adapter: {e}")
            return None

    elif provider == "salesforce":
        try:
            from .adapters.salesforce_client import SalesforceAdapter
            _crm_client = SalesforceAdapter()
            return _crm_client
        except Exception as e:
            logger.error(f"❌ Failed to init Salesforce adapter: {e}")
            return None

    else:
        logger.info("ℹ️ CRM_PROVIDER not set or set to 'none' — external sync disabled")
        return None


# =============================================================================
# Background Tasks
# =============================================================================

def sync_lead_to_crm(lead_id: UUID, db_url: str):
    """
    Background task: Syncs a local lead to the external CRM.
    Runs AFTER the API response is sent to keep latency low.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine_bg = create_engine(db_url)
    SessionBG = sessionmaker(bind=engine_bg)
    db = SessionBG()

    try:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            logger.error(f"❌ Background sync: Lead {lead_id} not found")
            return

        crm = get_crm_client()
        if not crm:
            logger.info(f"ℹ️ No CRM client configured, skipping sync for {lead_id}")
            return

        # Check if already synced
        if lead.external_id:
            logger.info(f"ℹ️ Lead {lead_id} already synced (external_id={lead.external_id})")
            return

        # Build data dict
        lead_data = {
            "name": lead.name,
            "email": lead.email or "",
            "phone": lead.phone or "",
            "company": lead.company or "",
            "summary": lead.summary or "",
        }

        # Search for existing contact first (dedup)
        existing = None
        if lead.email:
            existing = crm.search_contact(lead.email)

        if existing:
            lead.external_id = existing["external_id"]
            lead.provider = existing["provider"]
            lead.synced_at = datetime.utcnow()
            lead.sync_error = None
            logger.info(f"🔗 Linked to existing CRM contact: {existing['external_id']}")
        else:
            result = crm.create_contact(lead_data)
            lead.external_id = result["external_id"]
            lead.provider = result["provider"]
            lead.synced_at = datetime.utcnow()
            lead.sync_error = None
            logger.info(f"✅ Synced lead {lead_id} -> {result['provider']}:{result['external_id']}")

        db.commit()

        # Send internal notification email
        send_lead_notification(lead_data)

    except Exception as e:
        logger.error(f"❌ Background sync failed for {lead_id}: {e}")
        try:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                lead.sync_error = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# =============================================================================
# FastAPI App
# =============================================================================

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CRM Service",
    description="Lead management, external CRM sync (HubSpot/Salesforce), and email notifications",
    version="2.0.0",
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
async def startup_event():
    """Log CRM adapter status on startup."""
    provider = os.getenv("CRM_PROVIDER", "none")
    logger.info(f"🏢 CRM Provider configured: {provider}")
    crm = get_crm_client()
    if crm:
        logger.info(f"✅ CRM adapter ready: {type(crm).__name__}")
    else:
        logger.info("ℹ️ No external CRM adapter — leads will be stored locally only")

    email_sender = os.getenv("EMAIL_SENDER")
    if email_sender:
        logger.info(f"📧 Email configured: {email_sender}")
    else:
        logger.info("ℹ️ Email not configured — notifications disabled")


# =============================================================================
# Health
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check with CRM adapter status."""
    provider = os.getenv("CRM_PROVIDER", "none")
    crm = get_crm_client()
    return {
        "status": "ok",
        "service": "crm",
        "version": "2.0.0",
        "crm_provider": provider,
        "crm_connected": crm is not None,
        "email_configured": bool(os.getenv("EMAIL_SENDER")),
    }


# =============================================================================
# Lead CRUD Endpoints
# =============================================================================

@app.post("/leads", response_model=LeadResponse, status_code=201)
async def create_lead(
    lead: LeadCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Create a new lead locally, then sync to external CRM in the background.
    """
    try:
        db_lead = Lead(
            name=lead.name,
            email=lead.email,
            phone=lead.phone,
            company=lead.company,
            summary=lead.summary,
            status=LeadStatus.NEW,
        )
        db.add(db_lead)
        db.commit()
        db.refresh(db_lead)

        logger.info(f"✅ Created lead: {db_lead.name} (ID: {db_lead.id})")

        # Schedule background CRM sync (non-blocking)
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://agent_user:agent_password@postgres:5432/agent_db",
        )
        background_tasks.add_task(sync_lead_to_crm, db_lead.id, db_url)

        return db_lead

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error creating lead: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leads", response_model=List[LeadResponse])
async def list_leads(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    synced: bool = None,
    db: Session = Depends(get_db),
):
    """
    List all leads with optional filtering by status and sync state.
    """
    query = db.query(Lead)

    if status:
        query = query.filter(Lead.status == status)
    if synced is not None:
        if synced:
            query = query.filter(Lead.synced_at.isnot(None))
        else:
            query = query.filter(Lead.synced_at.is_(None))

    leads = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()
    return leads


@app.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: UUID, db: Session = Depends(get_db)):
    """Get a specific lead by ID."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@app.patch("/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID, lead_update: LeadUpdate, db: Session = Depends(get_db)
):
    """Update a lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update_data = lead_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            value = LeadStatus(value)
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)

    logger.info(f"✅ Updated lead: {lead.name} (ID: {lead.id})")
    return lead


@app.delete("/leads/{lead_id}", status_code=204)
async def delete_lead(lead_id: UUID, db: Session = Depends(get_db)):
    """Delete a lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    db.delete(lead)
    db.commit()

    logger.info(f"🗑️ Deleted lead: {lead_id}")
    return None


# =============================================================================
# CRM Sync Endpoints
# =============================================================================

@app.post("/leads/{lead_id}/sync", response_model=SyncResponse)
async def sync_lead(lead_id: UUID, db: Session = Depends(get_db)):
    """
    Manually trigger CRM sync for a specific lead.
    Useful for retrying failed syncs.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    crm = get_crm_client()
    if not crm:
        return SyncResponse(
            lead_id=lead_id,
            provider="none",
            success=False,
            message="No CRM provider configured. Set CRM_PROVIDER env var.",
        )

    try:
        lead_data = {
            "name": lead.name,
            "email": lead.email or "",
            "phone": lead.phone or "",
            "company": lead.company or "",
            "summary": lead.summary or "",
        }

        if lead.external_id:
            result = crm.update_contact(lead.external_id, lead_data)
        else:
            result = crm.create_contact(lead_data)

        lead.external_id = result["external_id"]
        lead.provider = result["provider"]
        lead.synced_at = datetime.utcnow()
        lead.sync_error = None
        db.commit()

        return SyncResponse(
            lead_id=lead_id,
            provider=result["provider"],
            external_id=result["external_id"],
            success=True,
            message=f"Lead synced to {result['provider']}",
        )

    except Exception as e:
        lead.sync_error = str(e)[:500]
        db.commit()
        return SyncResponse(
            lead_id=lead_id,
            provider=os.getenv("CRM_PROVIDER", "none"),
            success=False,
            message=f"Sync failed: {str(e)}",
        )


@app.post("/sync-all", response_model=List[SyncResponse])
async def sync_all_unsynced(db: Session = Depends(get_db)):
    """
    Sync all leads that haven't been synced yet.
    Useful for batch retry after an outage.
    """
    crm = get_crm_client()
    if not crm:
        raise HTTPException(
            status_code=400,
            detail="No CRM provider configured",
        )

    unsynced = db.query(Lead).filter(Lead.synced_at.is_(None)).all()
    results = []

    for lead in unsynced:
        try:
            lead_data = {
                "name": lead.name,
                "email": lead.email or "",
                "phone": lead.phone or "",
                "company": lead.company or "",
                "summary": lead.summary or "",
            }
            result = crm.create_contact(lead_data)
            lead.external_id = result["external_id"]
            lead.provider = result["provider"]
            lead.synced_at = datetime.utcnow()
            lead.sync_error = None
            db.commit()

            results.append(SyncResponse(
                lead_id=lead.id,
                provider=result["provider"],
                external_id=result["external_id"],
                success=True,
                message="Synced",
            ))
        except Exception as e:
            lead.sync_error = str(e)[:500]
            db.commit()
            results.append(SyncResponse(
                lead_id=lead.id,
                provider=os.getenv("CRM_PROVIDER", "none"),
                success=False,
                message=str(e),
            ))

    return results


# =============================================================================
# Email Endpoints
# =============================================================================

@app.post("/email/send")
async def send_email_endpoint(request: EmailRequest):
    """Send an email to a recipient."""
    result = send_email(request.to, request.subject, request.body)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


# =============================================================================
# Root Info
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "CRM Service",
        "version": "2.0.0",
        "endpoints": {
            "/health": "Health check (includes CRM status)",
            "/leads": "GET - List leads, POST - Create lead (auto-syncs to CRM)",
            "/leads/{id}": "GET/PATCH/DELETE - Manage specific lead",
            "/leads/{id}/sync": "POST - Manually sync a lead to CRM",
            "/sync-all": "POST - Sync all unsynced leads",
            "/email/send": "POST - Send an email",
        },
    }
