"""
CRM Service - Lead Management API.
Provides endpoints for creating, reading, and managing leads.
"""
from typing import List
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session
import logging

from .database import engine, get_db, Base
from .models import Lead, LeadStatus
from .schemas import LeadCreate, LeadResponse, LeadUpdate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CRM Service",
    description="Lead management and CRM API",
    version="1.0.0",
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "crm"}


@app.post("/leads", response_model=LeadResponse, status_code=201)
async def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    """
    Create a new lead.

    Args:
        lead: Lead data to create.
        db: Database session.

    Returns:
        The created lead.
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

        logger.info(f"Created lead: {db_lead.name} (ID: {db_lead.id})")
        return db_lead

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating lead: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leads", response_model=List[LeadResponse])
async def list_leads(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    db: Session = Depends(get_db),
):
    """
    List all leads with optional filtering.

    Args:
        skip: Number of records to skip (pagination).
        limit: Maximum number of records to return.
        status: Optional status filter.
        db: Database session.

    Returns:
        List of leads.
    """
    query = db.query(Lead)

    if status:
        query = query.filter(Lead.status == status)

    leads = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()
    return leads


@app.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: UUID, db: Session = Depends(get_db)):
    """
    Get a specific lead by ID.

    Args:
        lead_id: The lead UUID.
        db: Database session.

    Returns:
        The lead if found.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@app.patch("/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID, lead_update: LeadUpdate, db: Session = Depends(get_db)
):
    """
    Update a lead.

    Args:
        lead_id: The lead UUID.
        lead_update: Fields to update.
        db: Database session.

    Returns:
        The updated lead.
    """
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

    logger.info(f"Updated lead: {lead.name} (ID: {lead.id})")
    return lead


@app.delete("/leads/{lead_id}", status_code=204)
async def delete_lead(lead_id: UUID, db: Session = Depends(get_db)):
    """
    Delete a lead.

    Args:
        lead_id: The lead UUID.
        db: Database session.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    db.delete(lead)
    db.commit()

    logger.info(f"Deleted lead: {lead_id}")
    return None


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "CRM Service",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Health check",
            "/leads": "GET - List leads, POST - Create lead",
            "/leads/{id}": "GET/PATCH/DELETE - Manage specific lead",
        },
    }
