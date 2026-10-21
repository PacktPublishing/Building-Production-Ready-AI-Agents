from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from checkpoint_store import CheckpointStore
from webapp import app, checkpoint_store, sessions


client = TestClient(app)


def setup_function() -> None:
    sessions.clear()
    root = Path(__file__).parent.parent / "runtime" / "checkpoints"
    root.mkdir(parents=True, exist_ok=True)
    for path in root.glob("*.json"):
        path.unlink()


def create_session() -> str:
    response = client.post("/api/session")
    response.raise_for_status()
    return response.json()["session_id"]


def test_approval_gate_saves_checkpoint() -> None:
    session_id = create_session()

    response = client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "message": "Book a trip to Tokyo next month with budget 1800 for 2 travelers",
        },
    )
    payload = response.json()

    assert payload["status"] == "awaiting_approval"
    assert payload["checkpoint_ready"] is True
    assert "approval" in payload["message"].lower()
    assert checkpoint_store.checkpoint_path(session_id).exists()


def test_denied_approval_stops_booking() -> None:
    session_id = create_session()
    client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "message": "Book a trip to Tokyo next month with budget 1800 for 2 travelers",
        },
    )

    response = client.post(
        "/api/approval",
        json={"session_id": session_id, "approve": False},
    )
    payload = response.json()

    assert payload["status"] == "blocked"
    assert payload["booking_reference"] is None


def test_approval_then_resume_completes_booking() -> None:
    session_id = create_session()
    client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "message": "Book a trip to Tokyo next month with budget 1800 for 2 travelers",
        },
    )

    approval_response = client.post(
        "/api/approval",
        json={"session_id": session_id, "approve": True},
    )
    assert approval_response.json()["status"] == "ready_to_resume"

    resume_response = client.post(
        "/api/resume",
        json={"session_id": session_id},
    )
    payload = resume_response.json()

    assert payload["status"] == "completed"
    assert payload["booking_reference"].startswith("TRIP-")
    assert any(event["step"] == "checkpoint" for event in payload["trace"])


def test_low_risk_request_completes_automatically() -> None:
    session_id = create_session()

    response = client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "message": "Book a trip to Oslo next month with budget 700 for 1 traveler",
        },
    )
    payload = response.json()

    assert payload["status"] == "completed"
    assert payload["booking_reference"].startswith("TRIP-")