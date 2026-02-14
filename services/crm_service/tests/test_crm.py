"""
Automated Tests for CRM Service.
Tests the API endpoints locally without requiring external CRM connections.
Run: docker exec crm_service pytest /app/tests/ -v
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4

# We need to mock environment before importing the app
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_crm.db")
os.environ.setdefault("CRM_PROVIDER", "none")

from app.main import app
from app.database import Base, engine


# Override database for tests (use SQLite in-memory)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "sqlite:///./test_crm.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    """Test client for FastAPI."""
    from app.database import get_db

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealth:
    def test_health_check(self, client):
        """Health endpoint returns OK with CRM status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "crm"
        assert "crm_provider" in data
        assert "email_configured" in data

    def test_root_endpoint(self, client):
        """Root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "CRM Service"
        assert data["version"] == "2.0.0"


# =============================================================================
# Lead CRUD Tests
# =============================================================================

class TestLeadCRUD:
    def test_create_lead(self, client):
        """Creating a lead saves it locally and returns 201."""
        payload = {
            "name": "Test User",
            "email": "test@example.com",
            "company": "Test Corp",
            "summary": "Testing CRM",
        }
        response = client.post("/leads", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test User"
        assert data["email"] == "test@example.com"
        assert data["status"] == "new"
        assert data["id"] is not None

    def test_list_leads(self, client):
        """Listing leads returns all created leads."""
        # Create 2 leads
        client.post("/leads", json={"name": "Lead A", "email": "a@test.com"})
        client.post("/leads", json={"name": "Lead B", "email": "b@test.com"})

        response = client.get("/leads")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_lead_by_id(self, client):
        """Getting a lead by ID returns the correct lead."""
        create_resp = client.post("/leads", json={"name": "Specific Lead"})
        lead_id = create_resp.json()["id"]

        response = client.get(f"/leads/{lead_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Specific Lead"

    def test_get_nonexistent_lead(self, client):
        """Getting a non-existent lead returns 404."""
        fake_id = str(uuid4())
        response = client.get(f"/leads/{fake_id}")
        assert response.status_code == 404

    def test_update_lead(self, client):
        """Updating a lead changes the specified fields."""
        create_resp = client.post("/leads", json={"name": "Original Name"})
        lead_id = create_resp.json()["id"]

        response = client.patch(
            f"/leads/{lead_id}",
            json={"name": "Updated Name", "status": "contacted"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert response.json()["status"] == "contacted"

    def test_delete_lead(self, client):
        """Deleting a lead removes it from the database."""
        create_resp = client.post("/leads", json={"name": "To Delete"})
        lead_id = create_resp.json()["id"]

        delete_resp = client.delete(f"/leads/{lead_id}")
        assert delete_resp.status_code == 204

        get_resp = client.get(f"/leads/{lead_id}")
        assert get_resp.status_code == 404

    def test_filter_leads_by_status(self, client):
        """Filtering leads by status returns correct subset."""
        client.post("/leads", json={"name": "New Lead"})
        create2 = client.post("/leads", json={"name": "Contacted Lead"})
        lead_id = create2.json()["id"]
        client.patch(f"/leads/{lead_id}", json={"status": "contacted"})

        response = client.get("/leads?status=contacted")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Contacted Lead"


# =============================================================================
# Email Endpoint Tests
# =============================================================================

class TestEmail:
    @patch("app.main.send_email")
    def test_send_email_success(self, mock_send, client):
        """Email endpoint returns success when email sends."""
        mock_send.return_value = {"success": True, "message": "Email sent"}

        response = client.post("/email/send", json={
            "to": "test@example.com",
            "subject": "Test Subject",
            "body": "Test body",
        })
        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("app.main.send_email")
    def test_send_email_failure(self, mock_send, client):
        """Email endpoint returns 500 when email fails."""
        mock_send.return_value = {"success": False, "message": "Auth failed"}

        response = client.post("/email/send", json={
            "to": "test@example.com",
            "subject": "Test",
            "body": "Test",
        })
        assert response.status_code == 500


# =============================================================================
# CRM Sync Tests (Mocked)
# =============================================================================

class TestCRMSync:
    @patch("app.main.get_crm_client")
    def test_sync_no_provider(self, mock_get_crm, client):
        """Sync with no CRM provider returns graceful error."""
        mock_get_crm.return_value = None

        create_resp = client.post("/leads", json={"name": "Sync Test"})
        lead_id = create_resp.json()["id"]

        response = client.post(f"/leads/{lead_id}/sync")
        assert response.status_code == 200
        assert response.json()["success"] is False
        assert "No CRM provider" in response.json()["message"]
