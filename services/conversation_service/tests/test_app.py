from fastapi.testclient import TestClient
from services.conversation_service.app.main import app

# The TestClient allows us to make requests to our FastAPI app in tests
client = TestClient(app)

def test_health_check():
    """
    Tests if the /health endpoint returns a 200 OK status and the correct JSON.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
