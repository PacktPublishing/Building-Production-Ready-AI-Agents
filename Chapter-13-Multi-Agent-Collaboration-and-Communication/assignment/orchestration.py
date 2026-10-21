from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import asdict

from app_models import QuoteSummary, SessionResponse, SessionState, TraceEvent, now_iso
from checkpoint_store import CheckpointStore


MONTH_PATTERN = re.compile(
    r"(january|february|march|april|may|june|july|august|september|october|november|december|next month)",
    re.IGNORECASE,
)


def add_trace(state: SessionState, step: str, message: str, data: dict | None = None) -> None:
    state.trace.append(
        TraceEvent(
            ts=now_iso(),
            step=step,
            message=message,
            data=data or {},
        )
    )


def create_session() -> SessionState:
    session = SessionState(session_id=str(uuid.uuid4()))
    add_trace(session, "system", "Session created.")
    session.last_message = "Start by telling me where you want to go, your budget, the month, and how many travelers to plan for."
    return session


def apply_user_message(state: SessionState, message: str) -> list[str]:
    updates: list[str] = []

    destination_match = re.search(r"to\s+([A-Za-z ]+?)(?:\s+next|\s+in|\s+with|$)", message, re.IGNORECASE)
    budget_match = re.search(r"(?:budget\D*)?(\d{3,5})", message, re.IGNORECASE)
    traveler_match = re.search(r"(\d+)\s+(?:traveler|travelers|people|person)", message, re.IGNORECASE)
    month_match = MONTH_PATTERN.search(message)
    approval_match = re.search(r"approval\s*limit\D*(\d{3,5})", message, re.IGNORECASE)
    blocked_match = re.search(r"(?:blocked|block|hard)\s*limit\D*(\d{3,5})", message, re.IGNORECASE)

    if destination_match:
        state.request.destination = destination_match.group(1).strip().title()
        updates.append("destination")
    if budget_match:
        state.request.budget = int(budget_match.group(1))
        updates.append("budget")
    if traveler_match:
        state.request.travelers = int(traveler_match.group(1))
        updates.append("travelers")
    if month_match:
        state.request.month = month_match.group(1).lower()
        updates.append("month")
    if approval_match:
        state.policy.approval_limit = int(approval_match.group(1))
        updates.append("approval_limit")
    if blocked_match:
        state.policy.blocked_limit = int(blocked_match.group(1))
        updates.append("blocked_limit")

    if state.policy.blocked_limit <= state.policy.approval_limit:
        state.policy.blocked_limit = state.policy.approval_limit + 1

    return updates


def missing_fields(state: SessionState) -> list[str]:
    missing: list[str] = []
    if state.request.destination is None:
        missing.append("destination")
    if state.request.budget is None:
        missing.append("budget")
    if state.request.month is None:
        missing.append("month")
    if state.request.travelers is None:
        missing.append("travelers")
    return missing


def question_for(field_name: str) -> str:
    mapping = {
        "destination": "Where do you want to go?",
        "budget": "What budget should I stay under?",
        "month": "Which month should I book for?",
        "travelers": "How many travelers are included?",
    }
    return mapping[field_name]


def quote_factors(state: SessionState) -> tuple[float, float, int]:
    destination = (state.request.destination or "").lower()
    destination_factor = 1.0 + ((sum(ord(char) for char in destination) % 18) / 100)
    month_factor = 1.15 if (state.request.month or "") in {"june", "july", "august", "december"} else 1.0
    travelers = max(1, state.request.travelers or 1)

    return destination_factor, month_factor, travelers


async def fetch_flight_quote(state: SessionState) -> int:
    destination_factor, _, travelers = quote_factors(state)
    await asyncio.sleep(0)
    return int(420 * destination_factor * travelers)


async def fetch_hotel_quote(state: SessionState) -> int:
    _, month_factor, travelers = quote_factors(state)
    await asyncio.sleep(0)
    return int(260 * month_factor * travelers)


async def fetch_insurance_quote(state: SessionState) -> int:
    _, _, travelers = quote_factors(state)
    await asyncio.sleep(0)
    return 55 * travelers


async def gather_quotes(state: SessionState) -> QuoteSummary:
    flight, hotel, insurance = await asyncio.gather(
        fetch_flight_quote(state),
        fetch_hotel_quote(state),
        fetch_insurance_quote(state),
    )

    return QuoteSummary(flight=flight, hotel=hotel, insurance=insurance)


def estimate_quotes(state: SessionState) -> QuoteSummary:
    return asyncio.run(gather_quotes(state))


def serialize_trace(state: SessionState) -> list[dict]:
    return [asdict(event) for event in state.trace]


def to_response(state: SessionState, message: str) -> SessionResponse:
    state.last_message = message
    return SessionResponse(
        session_id=state.session_id,
        status=state.status,
        message=message,
        checkpoint_ready=state.checkpoint_ready,
        booking_reference=state.booking_reference,
        state=state.to_dict(),
        trace=serialize_trace(state),
    )


def save_checkpoint(state: SessionState, store: CheckpointStore, checkpoint_name: str) -> None:
    path = store.save(state, checkpoint_name)
    state.checkpoint_ready = True
    add_trace(
        state,
        "checkpoint",
        f"Saved checkpoint '{checkpoint_name}'.",
        {"path": path, "checkpoint": checkpoint_name},
    )


def finalize_booking(state: SessionState) -> str:
    state.booking_reference = f"TRIP-{state.session_id.split('-')[0].upper()}"
    state.status = "completed"
    state.checkpoint_ready = False
    add_trace(
        state,
        "executor",
        "Booking completed.",
        {
            "booking_reference": state.booking_reference,
            "total": state.quotes.total,
        },
    )
    return (
        f"Booking complete for {state.request.destination}. Reference: {state.booking_reference}. "
        f"Quoted total: ${state.quotes.total}."
    )


def evaluate_workflow(state: SessionState, store: CheckpointStore) -> SessionResponse:
    missing = missing_fields(state)
    if missing:
        state.status = "collecting_intent"
        add_trace(state, "planner", "Request still missing required fields.", {"missing": missing})
        return to_response(
            state,
            f"I still need {', '.join(missing)}. {question_for(missing[0])}",
        )

    add_trace(state, "planner", "Gathering flight, hotel, and insurance quotes in parallel.")
    state.quotes = estimate_quotes(state)
    add_trace(
        state,
        "planner",
        "Estimated travel quotes.",
        {
            "flight": state.quotes.flight,
            "hotel": state.quotes.hotel,
            "insurance": state.quotes.insurance,
            "total": state.quotes.total,
        },
    )
    save_checkpoint(state, store, "post_quote_review")

    if state.quotes.total >= state.policy.blocked_limit:
        state.status = "blocked"
        add_trace(
            state,
            "monitor",
            "Workflow blocked by policy.",
            {
                "total": state.quotes.total,
                "blocked_limit": state.policy.blocked_limit,
            },
        )
        return to_response(
            state,
            (
                f"This run is blocked because the quoted total ${state.quotes.total} is at or above "
                f"the hard limit of ${state.policy.blocked_limit}."
            ),
        )

    if state.quotes.total >= state.policy.approval_limit:
        state.status = "awaiting_approval"
        save_checkpoint(state, store, "awaiting_approval")
        add_trace(
            state,
            "monitor",
            "Approval gate triggered.",
            {
                "total": state.quotes.total,
                "approval_limit": state.policy.approval_limit,
            },
        )
        return to_response(
            state,
            (
                f"The quoted total is ${state.quotes.total}. That crosses the approval limit of "
                f"${state.policy.approval_limit}. Approve or deny the booking before resuming."
            ),
        )

    add_trace(
        state,
        "monitor",
        "Policy allowed autonomous completion.",
        {
            "total": state.quotes.total,
            "approval_limit": state.policy.approval_limit,
        },
    )
    return to_response(state, finalize_booking(state))


def handle_chat(state: SessionState, message: str, store: CheckpointStore) -> SessionResponse:
    add_trace(state, "user", "Received user message.", {"message": message})

    if state.status == "awaiting_approval":
        return to_response(
            state,
            "This run is waiting for approval. Use the approve or deny action before sending more booking details.",
        )

    updates = apply_user_message(state, message)
    if updates:
        add_trace(state, "planner", "Applied extracted updates.", {"updated_fields": updates})
    else:
        add_trace(
            state,
            "planner",
            "No structured fields were extracted from the latest message.",
            {"message": message},
        )
    return evaluate_workflow(state, store)


def handle_approval(state: SessionState, approve: bool, store: CheckpointStore) -> SessionResponse:
    if state.status != "awaiting_approval":
        return to_response(state, "There is no pending approval for this session.")

    if not approve:
        state.status = "blocked"
        state.checkpoint_ready = False
        add_trace(state, "approval", "Approval denied.")
        return to_response(state, "Approval denied. The workflow stopped before booking execution.")

    state.status = "ready_to_resume"
    save_checkpoint(state, store, "approved_resume")
    add_trace(state, "approval", "Approval granted. Resuming workflow automatically.")
    return handle_resume(state, store)


def handle_resume(state: SessionState, store: CheckpointStore) -> SessionResponse:
    if state.status != "ready_to_resume":
        return to_response(state, "This session is not ready to resume from a checkpoint yet.")

    restored = store.load(state.session_id)
    if restored is None:
        return to_response(state, "No checkpoint was found for this session.")

    if restored.session_id != state.session_id:
        return to_response(state, "Checkpoint/session mismatch detected. Resume was canceled for safety.")

    state.request = restored.request
    state.policy = restored.policy
    state.quotes = restored.quotes
    state.current_checkpoint = restored.current_checkpoint
    state.trace = restored.trace
    add_trace(state, "checkpoint", "Restored state from checkpoint.", {"checkpoint": state.current_checkpoint})

    # Revalidate policy after restore before executing side effects.
    if state.quotes.total >= state.policy.blocked_limit:
        state.status = "blocked"
        state.checkpoint_ready = False
        add_trace(
            state,
            "monitor",
            "Resume blocked after policy revalidation.",
            {"total": state.quotes.total, "blocked_limit": state.policy.blocked_limit},
        )
        return to_response(
            state,
            (
                f"Resume blocked: quoted total ${state.quotes.total} is at or above "
                f"the hard limit ${state.policy.blocked_limit}."
            ),
        )

    # If a human already approved this exact quote set, continue to execution.
    if state.current_checkpoint == "approved_resume":
        add_trace(
            state,
            "monitor",
            "Resume continuing with previously granted approval.",
            {"total": state.quotes.total, "approval_limit": state.policy.approval_limit},
        )
        return to_response(state, finalize_booking(state))

    if state.quotes.total >= state.policy.approval_limit:
        state.status = "awaiting_approval"
        state.checkpoint_ready = True
        add_trace(
            state,
            "monitor",
            "Resume requires renewed approval after policy revalidation.",
            {"total": state.quotes.total, "approval_limit": state.policy.approval_limit},
        )
        return to_response(
            state,
            (
                f"Resume paused: quoted total ${state.quotes.total} crosses the approval limit "
                f"${state.policy.approval_limit}. Approve again to continue."
            ),
        )

    return to_response(state, finalize_booking(state))


def response_for_session(state: SessionState) -> SessionResponse:
    return to_response(state, state.last_message or "Session ready.")