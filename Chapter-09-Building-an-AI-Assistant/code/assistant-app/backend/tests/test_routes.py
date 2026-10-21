"""Tests for API routes with mocked assistant."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.main import app, _get_assistant
from backend.schemas import (
    Action,
    Category,
    Priority,
    TriageResult,
)


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def _override(self, connected: bool):
        mock = MagicMock()
        mock.model_name = "mistral:latest"
        mock.check_health = AsyncMock(return_value=connected)
        app.dependency_overrides[_get_assistant] = lambda: mock

    def test_healthy(self, client):
        self._override(connected=True)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
        app.dependency_overrides.clear()

    def test_degraded(self, client):
        self._override(connected=False)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "degraded"
        app.dependency_overrides.clear()


class TestTriageEndpoint:
    def test_triage_success(self, client):
        mock = MagicMock()
        mock.model_name = "mistral:latest"
        mock.triage_batch.return_value = (
            [
                TriageResult(
                    ticket_id="T-001",
                    category=Category.HARDWARE,
                    priority=Priority.HIGH,
                    summary="Laptop won't turn on.",
                    recommended_actions=[Action.RESTART_DEVICE],
                    reasoning="Hardware failure.",
                )
            ],
            150.5,
        )
        app.dependency_overrides[_get_assistant] = lambda: mock

        resp = client.post(
            "/api/triage",
            json={
                "tickets": [
                    {
                        "id": "T-001",
                        "message": "My laptop won't turn on",
                        "sender": "alice@company.com",
                    }
                ]
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["category"] == "Hardware Issue"
        assert data["model_used"] == "mistral:latest"
        app.dependency_overrides.clear()

    def test_empty_tickets_rejected(self, client):
        resp = client.post("/api/triage", json={"tickets": []})
        assert resp.status_code == 422

    def test_invalid_payload(self, client):
        resp = client.post("/api/triage", json={"wrong": "field"})
        assert resp.status_code == 422
