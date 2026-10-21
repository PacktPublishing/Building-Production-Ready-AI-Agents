from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@dataclass
class TravelRequest:
    destination: str | None = None
    budget: int | None = None
    month: str | None = None
    travelers: int | None = None


@dataclass
class PolicyConfig:
    approval_limit: int = 1200
    blocked_limit: int = 2200


@dataclass
class QuoteSummary:
    flight: int = 0
    hotel: int = 0
    insurance: int = 0

    @property
    def total(self) -> int:
        return self.flight + self.hotel + self.insurance


@dataclass
class TraceEvent:
    ts: str
    step: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionState:
    session_id: str
    request: TravelRequest = field(default_factory=TravelRequest)
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    quotes: QuoteSummary = field(default_factory=QuoteSummary)
    status: Literal[
        "collecting_intent",
        "awaiting_approval",
        "ready_to_resume",
        "completed",
        "blocked",
    ] = "collecting_intent"
    current_checkpoint: str | None = None
    checkpoint_ready: bool = False
    booking_reference: str | None = None
    last_message: str = ""
    trace: list[TraceEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["quotes"]["total"] = self.quotes.total
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionState":
        request = TravelRequest(**payload.get("request", {}))
        policy = PolicyConfig(**payload.get("policy", {}))
        quotes_payload = payload.get("quotes", {})
        quotes = QuoteSummary(
            flight=quotes_payload.get("flight", 0),
            hotel=quotes_payload.get("hotel", 0),
            insurance=quotes_payload.get("insurance", 0),
        )
        trace = [TraceEvent(**event) for event in payload.get("trace", [])]
        return cls(
            session_id=payload["session_id"],
            request=request,
            policy=policy,
            quotes=quotes,
            status=payload.get("status", "collecting_intent"),
            current_checkpoint=payload.get("current_checkpoint"),
            checkpoint_ready=payload.get("checkpoint_ready", False),
            booking_reference=payload.get("booking_reference"),
            last_message=payload.get("last_message", ""),
            trace=trace,
        )


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1)


class ResumeRequest(BaseModel):
    session_id: str


class ApprovalRequest(BaseModel):
    session_id: str
    approve: bool


class SessionResponse(BaseModel):
    session_id: str
    status: str
    message: str
    checkpoint_ready: bool
    booking_reference: str | None
    state: dict[str, Any]
    trace: list[dict[str, Any]]