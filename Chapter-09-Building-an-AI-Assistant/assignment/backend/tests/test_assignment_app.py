from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "model" in response.json()


def test_chat_endpoint_returns_response():
    response = client.post(
        "/api/chat",
        json={"session_id": "test", "message": "My wifi keeps dropping."},
    )
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert data["selected_tool"] == "network_diagnostic"


def test_confirm_without_pending_action():
    response = client.post(
        "/api/confirm",
        json={"session_id": "new-session", "approve": True},
    )
    assert response.status_code == 200
    assert "no pending action" in response.json()["reply"].lower()
