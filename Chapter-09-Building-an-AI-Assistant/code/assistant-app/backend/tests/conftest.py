"""Shared test fixtures."""

import pytest

from backend.utils.config import Settings
from backend.schemas import TicketMessage


@pytest.fixture
def settings() -> Settings:
    return Settings(ollama_model="qwen2.5:1.5b")


@pytest.fixture
def sample_tickets() -> list[TicketMessage]:
    return [
        TicketMessage(
            id="T-001",
            message="My laptop won't turn on after the latest Windows update. I've tried holding the power button for 30 seconds but nothing happens. I have a client presentation in 2 hours!",
            sender="alice@company.com",
        ),
        TicketMessage(
            id="T-002",
            message="I can't access the shared drive. It keeps saying 'access denied'. I was able to access it yesterday. My colleague sitting next to me can still access it fine.",
            sender="bob@company.com",
        ),
        TicketMessage(
            id="T-003",
            message="I received a suspicious email from what looks like our CEO asking me to wire $50,000 to a new vendor. The email address looks slightly different from the real one. Should I report this?",
            sender="carol@company.com",
        ),
    ]
