from __future__ import annotations

import random
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@dataclass
class ToggleConfig:
    manual_quote_check: bool = True
    manual_risk_check: bool = True
    manual_trade_approval: bool = True


@dataclass
class Event:
    ts: str
    step: str
    message: str


@dataclass
class SimulationSession:
    session_id: str
    target_profit: float
    starting_cash: float
    max_cycles: int
    toggles: ToggleConfig
    price: float
    cycle: int = 0
    cash: float = 0.0
    shares: int = 0
    avg_cost: float = 0.0
    status: str = "running"
    pending_step: str | None = None
    current_action: str = "hold"
    current_reason: str = ""
    current_risk: str = "low"
    current_risk_note: str = ""
    queue: list[str] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)

    def net_worth(self) -> float:
        return self.cash + (self.shares * self.price)

    def profit(self) -> float:
        return self.net_worth() - self.starting_cash


class CreateSessionRequest(BaseModel):
    target_profit: float = Field(default=300, gt=0)
    starting_cash: float = Field(default=5000, gt=0)
    max_cycles: int = Field(default=12, ge=1, le=100)
    manual_quote_check: bool = True
    manual_risk_check: bool = True
    manual_trade_approval: bool = True


class ManualDecisionRequest(BaseModel):
    approve: bool
    note: str | None = None


class StockBrokerService:
    def next_quote(self, current: float) -> float:
        # Random walk from -6% to +6%
        pct = random.uniform(-0.06, 0.06)
        return max(5.0, round(current * (1 + pct), 2))


app = FastAPI(title="Program Autonomy Simulator")
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

sessions: dict[str, SimulationSession] = {}
broker = StockBrokerService()


def add_event(session: SimulationSession, step: str, message: str) -> None:
    session.events.append(Event(ts=now_iso(), step=step, message=message))


def assess_risk(session: SimulationSession, price: float) -> tuple[str, str]:
    if session.shares == 0:
        return "low", "No open position yet."

    drawdown = 0.0
    if session.avg_cost > 0:
        drawdown = (session.avg_cost - price) / session.avg_cost

    if drawdown >= 0.12:
        return "high", f"Current drawdown is {drawdown:.1%}; consider reducing exposure."
    if drawdown >= 0.06:
        return "medium", f"Current drawdown is {drawdown:.1%}; monitor closely."
    return "low", f"Current drawdown is {drawdown:.1%}; within tolerance."


def choose_action(session: SimulationSession, price: float) -> tuple[str, str]:
    profit = session.profit()

    if profit >= session.target_profit and session.shares > 0:
        return "sell", "Profit target reached, lock gains."

    if session.shares == 0 and session.cash >= price:
        return "buy", "Open a position to pursue target profit."

    if session.shares > 0 and price < session.avg_cost * 0.9:
        return "sell", "Stop-loss triggered below 10% from average cost."

    return "hold", "Wait for a stronger setup."


def begin_cycle(session: SimulationSession) -> None:
    if session.cycle >= session.max_cycles:
        session.status = "completed"
        add_event(session, "finish", "Reached max cycle count.")
        return

    # Stop automatically if target reached and there is no open position.
    if session.profit() >= session.target_profit and session.shares == 0:
        session.status = "completed"
        add_event(session, "finish", "Target achieved and no open position remains.")
        return

    session.cycle += 1
    session.price = broker.next_quote(session.price)
    action, reason = choose_action(session, session.price)
    risk_level, risk_note = assess_risk(session, session.price)

    session.current_action = action
    session.current_reason = reason
    session.current_risk = risk_level
    session.current_risk_note = risk_note

    add_event(
        session,
        "quote",
        f"Cycle {session.cycle}: broker quote is ${session.price:.2f}. Proposed action: {action}.",
    )
    add_event(session, "policy", f"Action rationale: {reason}")
    add_event(session, "risk", f"Risk level: {risk_level}. {risk_note}")

    queue: list[str] = []
    if session.toggles.manual_quote_check:
        queue.append("quote_check")
    if session.toggles.manual_risk_check:
        queue.append("risk_check")
    if session.toggles.manual_trade_approval and action in {"buy", "sell"}:
        queue.append("trade_approval")
    queue.append("execute")

    session.queue = queue


def execute_trade(session: SimulationSession) -> None:
    action = session.current_action

    if action == "buy":
        if session.cash >= session.price:
            total_cost_before = session.avg_cost * session.shares
            session.cash -= session.price
            session.shares += 1
            session.avg_cost = (total_cost_before + session.price) / session.shares
            add_event(session, "execute", f"Bought 1 share at ${session.price:.2f}.")
        else:
            add_event(session, "execute", "Skipped buy: not enough cash.")

    elif action == "sell":
        if session.shares > 0:
            proceeds = session.shares * session.price
            sold = session.shares
            session.cash += proceeds
            session.shares = 0
            session.avg_cost = 0.0
            add_event(session, "execute", f"Sold {sold} share(s) at ${session.price:.2f}.")
        else:
            add_event(session, "execute", "Skipped sell: no shares to sell.")

    else:
        add_event(session, "execute", "Held position this cycle.")

    add_event(
        session,
        "portfolio",
        (
            f"Portfolio after cycle {session.cycle}: cash=${session.cash:.2f}, shares={session.shares}, "
            f"net_worth=${session.net_worth():.2f}, profit=${session.profit():.2f}."
        ),
    )


def run_until_pause_or_finish(
    session: SimulationSession,
    approved_step: str | None = None,
    approved: bool = True,
    note: str | None = None,
) -> None:
    while True:
        if session.status == "completed":
            return

        if not session.queue:
            begin_cycle(session)
            if session.status == "completed":
                return

        step = session.queue[0]

        if step in {"quote_check", "risk_check", "trade_approval"}:
            if approved_step == step:
                session.queue.pop(0)
                add_event(
                    session,
                    "manual",
                    f"Manual step {step}: {'approved' if approved else 'rejected'}"
                    + (f" ({note})" if note else ""),
                )
                if not approved:
                    session.current_action = "hold"
                    # If reviewer rejects once, skip remaining manual checkpoints for this cycle.
                    session.queue = [s for s in session.queue if s == "execute"]
                approved_step = None
                note = None
                continue

            session.status = "awaiting_manual"
            session.pending_step = step
            add_event(session, "manual", f"Paused for manual step: {step}.")
            return

        if step == "execute":
            session.queue.pop(0)
            execute_trade(session)
            session.status = "running"
            session.pending_step = None
            continue

        raise RuntimeError(f"Unknown queue step: {step}")


def serialize(session: SimulationSession) -> dict:
    return {
        "session_id": session.session_id,
        "status": session.status,
        "pending_step": session.pending_step,
        "cycle": session.cycle,
        "max_cycles": session.max_cycles,
        "target_profit": session.target_profit,
        "starting_cash": session.starting_cash,
        "cash": round(session.cash, 2),
        "shares": session.shares,
        "avg_cost": round(session.avg_cost, 2),
        "price": round(session.price, 2),
        "net_worth": round(session.net_worth(), 2),
        "profit": round(session.profit(), 2),
        "current_action": session.current_action,
        "current_reason": session.current_reason,
        "current_risk": session.current_risk,
        "current_risk_note": session.current_risk_note,
        "toggles": asdict(session.toggles),
        "events": [asdict(e) for e in session.events[-60:]],
    }


@app.get("/")
def root() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.post("/api/sessions")
def create_session(payload: CreateSessionRequest) -> dict:
    session_id = uuid.uuid4().hex
    opening_price = round(random.uniform(80, 160), 2)
    session = SimulationSession(
        session_id=session_id,
        target_profit=payload.target_profit,
        starting_cash=payload.starting_cash,
        max_cycles=payload.max_cycles,
        toggles=ToggleConfig(
            manual_quote_check=payload.manual_quote_check,
            manual_risk_check=payload.manual_risk_check,
            manual_trade_approval=payload.manual_trade_approval,
        ),
        price=opening_price,
        cash=payload.starting_cash,
    )
    add_event(session, "start", f"Session created with opening quote ${opening_price:.2f}.")
    sessions[session_id] = session
    run_until_pause_or_finish(session)
    return serialize(session)


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return serialize(session)


@app.post("/api/sessions/{session_id}/advance")
def advance_session(session_id: str) -> dict:
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "awaiting_manual":
        raise HTTPException(status_code=400, detail="Session is waiting for manual decision")
    run_until_pause_or_finish(session)
    return serialize(session)


@app.post("/api/sessions/{session_id}/manual")
def manual_decision(session_id: str, payload: ManualDecisionRequest) -> dict:
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "awaiting_manual" or not session.pending_step:
        raise HTTPException(status_code=400, detail="No pending manual decision")

    step = session.pending_step
    session.status = "running"
    session.pending_step = None

    run_until_pause_or_finish(
        session,
        approved_step=step,
        approved=payload.approve,
        note=payload.note,
    )
    return serialize(session)
