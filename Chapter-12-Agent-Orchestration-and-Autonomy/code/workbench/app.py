from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from ollama import Client
from pydantic import BaseModel, Field


@dataclass
class Plan:
    destination: str | None
    budget: int | None
    month: str | None
    travelers: int | None


@dataclass
class PolicyConfig:
    approval_limit: int
    blocked_limit: int


@dataclass
class Event:
    step: str
    message: str


class SimulationRequest(BaseModel):
    prompt: str = Field(default="Book a trip to Tokyo next month with budget 1800 for 1 traveler")
    strategy: str = Field(default="sequential")
    blocks: list[str] = Field(default_factory=lambda: [
        "collect_intent",
        "policy_check",
        "flight_search",
        "hotel_search",
        "insurance_quote",
        "approval_gate",
        "booking",
    ])
    approval_limit: int | None = None
    blocked_limit: int | None = None
    approval_decision: str | None = None
    flight_quote: int | None = None
    hotel_quote: int | None = None
    insurance_quote: int | None = None


class OllamaIntentParser:
    def __init__(self) -> None:
        self.host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
        self.client = Client(host=self.host)

    def parse_plan(self, prompt: str) -> Plan | None:
        system_prompt = (
            "Extract travel intent fields from user text. "
            "Return ONLY valid compact JSON with keys: destination, budget, month, travelers. "
            "Use null for unknown values. budget and travelers must be integers when present."
        )
        user_prompt = f"User request: {prompt}"

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response["message"]["content"].strip()
            match = re.search(r"\{.*\}", content, re.DOTALL)
            raw = match.group(0) if match else content
            data = json.loads(raw)

            budget = data.get("budget")
            travelers = data.get("travelers")

            return Plan(
                destination=(str(data.get("destination")).strip().title() if data.get("destination") else None),
                budget=int(budget) if budget is not None else None,
                month=(str(data.get("month")).strip().lower() if data.get("month") else None),
                travelers=int(travelers) if travelers is not None else None,
            )
        except Exception:
            return None


def parse_prompt_regex(prompt: str) -> Plan:
    destination_match = re.search(r"to\s+([A-Za-z ]+?)(?:\s+next|\s+in|\s+with|$)", prompt, re.IGNORECASE)
    budget_match = re.search(r"(?:budget\D*)?(\d{3,5})", prompt, re.IGNORECASE)
    month_match = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december|next month)",
        prompt,
        re.IGNORECASE,
    )
    traveler_match = re.search(r"(\d+)\s+(?:traveler|travelers|people|person)", prompt, re.IGNORECASE)

    return Plan(
        destination=destination_match.group(1).strip().title() if destination_match else None,
        budget=int(budget_match.group(1)) if budget_match else None,
        month=month_match.group(1).lower() if month_match else None,
        travelers=int(traveler_match.group(1)) if traveler_match else None,
    )


def merge_plan(primary: Plan, fallback: Plan) -> Plan:
    return Plan(
        destination=primary.destination or fallback.destination,
        budget=primary.budget if primary.budget is not None else fallback.budget,
        month=primary.month or fallback.month,
        travelers=primary.travelers if primary.travelers is not None else fallback.travelers,
    )


def parse_prompt(prompt: str) -> Plan:
    regex_plan = parse_prompt_regex(prompt)
    llm_plan = OllamaIntentParser().parse_plan(prompt)
    if llm_plan is None:
        return regex_plan
    return merge_plan(llm_plan, regex_plan)


def parse_policy(prompt: str, approval_override: int | None, blocked_override: int | None) -> tuple[PolicyConfig, list[str]]:
    questions: list[str] = []

    approval_match = re.search(
        r"(?:approval\s*limit|approval\s*above|approve\s*up\s*to|autonomous\s*limit)\D*(\d{3,5})",
        prompt,
        re.IGNORECASE,
    )
    blocked_match = re.search(
        r"(?:block\s*limit|block\s*above|hard\s*limit|max\s*without\s*exception)\D*(\d{3,5})",
        prompt,
        re.IGNORECASE,
    )

    if approval_override is not None:
        approval = approval_override
    elif approval_match:
        approval = int(approval_match.group(1))
    else:
        approval = 1200
        questions.append("What approval limit should I use for autonomous booking?")

    if blocked_override is not None:
        blocked = blocked_override
    elif blocked_match:
        blocked = int(blocked_match.group(1))
    else:
        blocked = 2000
        questions.append("What hard stop limit should block execution?")

    if blocked <= approval:
        blocked = approval + 1

    return PolicyConfig(approval_limit=approval, blocked_limit=blocked), questions


def required_fields_for_blocks(blocks: list[str]) -> list[str]:
    fields = ["destination", "budget"]
    if any(block in blocks for block in ["flight_search", "hotel_search", "booking"]):
        fields.extend(["month", "travelers"])
    return list(dict.fromkeys(fields))


def missing_fields(plan: Plan, fields: list[str]) -> list[str]:
    out: list[str] = []
    for field in fields:
        if getattr(plan, field) is None:
            out.append(field)
    return out


def field_question(field_name: str) -> str:
    mapping = {
        "destination": "Where do you want to go?",
        "budget": "What is your budget in dollars?",
        "month": "What month should I plan for?",
        "travelers": "How many travelers are included?",
    }
    return mapping[field_name]


def route_for_plan(plan: Plan, policy: PolicyConfig) -> str:
    if plan.budget is None:
        return "needs_intent"
    if plan.budget > policy.blocked_limit:
        return "blocked"
    if plan.budget > policy.approval_limit:
        return "approval"
    return "approved"


def estimate_quote_total(
    plan: Plan,
    blocks: list[str],
    manual_quotes: dict[str, int] | None = None,
) -> tuple[int, dict[str, int]]:
    destination = (plan.destination or "").lower()
    destination_factor = 1.0 + ((sum(ord(c) for c in destination) % 20) / 100)

    month = (plan.month or "").lower()
    peak_months = {"june", "july", "august", "december"}
    month_factor = 1.12 if month in peak_months else 1.0

    travelers = max(1, plan.travelers or 1)

    base_prices = {
        "flight_search": 420,
        "hotel_search": 310,
        "insurance_quote": 65,
    }

    components: dict[str, int] = {}
    manual_quotes = manual_quotes or {}
    for block in ("flight_search", "hotel_search", "insurance_quote"):
        if block not in blocks:
            continue
        if block in manual_quotes:
            components[block] = manual_quotes[block]
            continue
        base = base_prices[block]
        traveler_factor = travelers if block != "hotel_search" else max(1, int(round(travelers * 0.7)))
        price = int(round(base * destination_factor * month_factor * traveler_factor))
        components[block] = price

    total = sum(components.values())
    return total, components


def routed_route_decision(
    plan: Plan,
    policy: PolicyConfig,
    blocks: list[str],
    manual_quotes: dict[str, int] | None = None,
) -> tuple[str, str, int, dict[str, int]]:
    if plan.budget is None:
        return "needs_intent", "Missing budget in user intent.", 0, {}

    estimated_total, components = estimate_quote_total(plan, blocks, manual_quotes)

    if estimated_total >= policy.blocked_limit:
        return (
            "blocked",
            f"Quoted total {estimated_total} is at or above hard policy limit {policy.blocked_limit}.",
            estimated_total,
            components,
        )

    if estimated_total >= policy.approval_limit:
        return (
            "approval",
            f"Quoted total {estimated_total} is at or above approval limit {policy.approval_limit}.",
            estimated_total,
            components,
        )

    if estimated_total > plan.budget:
        return (
            "approval",
            f"Quoted total {estimated_total} exceeds user budget {plan.budget}.",
            estimated_total,
            components,
        )

    return "approved", f"Quoted total {estimated_total} is within budget and policy limits.", estimated_total, components


def visited_blocks_for_route(blocks: list[str], route: str) -> list[str]:
    if route == "approved":
        return [b for b in blocks if b != "blocked_end"]
    if route == "approval":
        # Keep data collection visible in sequential/parallel runs, then stop before booking.
        return [b for b in blocks if b in {"collect_intent", "policy_check", "flight_search", "hotel_search", "insurance_quote", "approval_gate"}]
    if route == "blocked":
        out = [b for b in blocks if b in {"collect_intent", "policy_check", "flight_search", "hotel_search", "insurance_quote"}]
        if "blocked_end" in blocks:
            out.append("blocked_end")
        return out
    if route == "denied":
        return [b for b in blocks if b in {"collect_intent", "policy_check", "flight_search", "hotel_search", "insurance_quote", "approval_gate"}]
    return []


def visited_blocks_for_routed(
    blocks: list[str],
    route: str,
    reason: str,
    approval_decision: str | None = None,
) -> list[str]:
    if route == "approved":
        # If approval was explicitly granted, only continue with post-gate steps.
        if (approval_decision or "").lower() == "approve" and "approval_gate" in blocks:
            idx = blocks.index("approval_gate")
            return [b for b in blocks[idx + 1 :] if b != "blocked_end"]
        return [b for b in blocks if b not in {"approval_gate", "blocked_end"}]

    if route == "approval":
        if "approval_gate" in blocks:
            idx = blocks.index("approval_gate")
            return blocks[: idx + 1]
        return list(blocks)

    if route == "blocked":
        # Routed mode always gathers quote components first, then forks.
        blocked_path = [b for b in blocks if b in {"collect_intent", "policy_check", "flight_search", "hotel_search", "insurance_quote"}]
        if "blocked_end" in blocks:
            blocked_path.append("blocked_end")
        return blocked_path

    if route == "denied":
        if "approval_gate" in blocks:
            idx = blocks.index("approval_gate")
            return blocks[: idx + 1]
        return [b for b in blocks if b in {"collect_intent", "policy_check", "approval_gate"}]

    return []


def build_itinerary(plan: Plan, quote_components: dict[str, int], total: int) -> dict:
    destination = plan.destination or "TBD"
    month = plan.month or "TBD"
    travelers = plan.travelers or 1
    return {
        "destination": destination,
        "month": month,
        "travelers": travelers,
        "flight": quote_components.get("flight_search"),
        "hotel": quote_components.get("hotel_search"),
        "insurance": quote_components.get("insurance_quote"),
        "total": total,
    }


def build_block_results(
    plan: Plan,
    policy: PolicyConfig,
    route: str,
    route_reason: str,
    visited_blocks: list[str],
    quote_components: dict[str, int],
    estimated_total: int,
    approval_decision: str | None,
    manual_quote_keys: set[str] | None = None,
) -> list[dict]:
    results: list[dict] = []
    manual_quote_keys = manual_quote_keys or set()

    def push(block_id: str, response: dict, status: str = "done") -> None:
        results.append({"block": block_id, "status": status, "response": response})

    for block_id in visited_blocks:
        if block_id == "collect_intent":
            push(
                block_id,
                {
                    "destination": plan.destination,
                    "budget": plan.budget,
                    "month": plan.month,
                    "travelers": plan.travelers,
                },
            )
        elif block_id == "policy_check":
            push(
                block_id,
                {
                    "approval_limit": policy.approval_limit,
                    "blocked_limit": policy.blocked_limit,
                    "route": route,
                    "reason": route_reason,
                },
            )
        elif block_id == "flight_search":
            push(
                block_id,
                {
                    "quote": quote_components.get("flight_search", 0),
                    "currency": "USD",
                    "source": "override" if "flight_search" in manual_quote_keys else "estimated",
                },
            )
        elif block_id == "hotel_search":
            push(
                block_id,
                {
                    "quote": quote_components.get("hotel_search", 0),
                    "currency": "USD",
                    "source": "override" if "hotel_search" in manual_quote_keys else "estimated",
                },
            )
        elif block_id == "insurance_quote":
            push(
                block_id,
                {
                    "quote": quote_components.get("insurance_quote", 0),
                    "currency": "USD",
                    "source": "override" if "insurance_quote" in manual_quote_keys else "estimated",
                },
            )
        elif block_id == "approval_gate":
            decision = (approval_decision or "pending").lower()
            approved: bool | None = None
            if decision == "approve":
                approved = True
            elif decision == "deny":
                approved = False
            push(block_id, {"decision": decision, "approved": approved})
        elif block_id == "booking":
            push(
                block_id,
                {
                    "executed": True,
                    "total": estimated_total,
                },
            )
        elif block_id == "blocked_end":
            push(
                block_id,
                {
                    "blocked": True,
                    "reason": route_reason,
                },
            )

    existing_blocks = {item["block"] for item in results}

    if approval_decision in {"approve", "deny"} and "approval_gate" not in existing_blocks:
        approved = True if approval_decision == "approve" else False
        push("approval_gate", {"decision": approval_decision, "approved": approved})

    if route in {"blocked", "denied", "approval"} and "booking" not in existing_blocks:
        if route == "approval":
            push("booking", {"executed": False, "reason": "Waiting for approval."}, status="skipped")
        elif route == "denied":
            push("booking", {"executed": False, "reason": "Approval denied."}, status="skipped")
        else:
            push("booking", {"executed": False, "reason": "Blocked by hard policy limit."}, status="skipped")

    if route == "blocked" and "blocked_end" not in existing_blocks:
        push("blocked_end", {"blocked": True, "reason": route_reason}, status="done")

    return results


def simulate(request: SimulationRequest) -> dict:
    strategy = request.strategy.lower()
    blocks = request.blocks
    plan = parse_prompt(request.prompt)
    policy, policy_questions = parse_policy(request.prompt, request.approval_limit, request.blocked_limit)

    events: list[Event] = [Event(step="planner", message=f"Parsed initial plan: {plan}")]
    questions: list[str] = []

    route_reason = ""
    estimated_total = 0
    quote_components: dict[str, int] = {}
    manual_quotes = {
        "flight_search": request.flight_quote,
        "hotel_search": request.hotel_quote,
        "insurance_quote": request.insurance_quote,
    }
    manual_quotes = {k: v for k, v in manual_quotes.items() if v is not None and v >= 0}
    estimated_total, quote_components = estimate_quote_total(plan, blocks, manual_quotes)

    if strategy == "sequential":
        for block in blocks:
            if block == "collect_intent":
                needed = missing_fields(plan, ["destination", "budget"])
            elif block in {"flight_search", "hotel_search", "booking"}:
                needed = missing_fields(plan, ["month", "travelers"])
            elif block == "policy_check":
                needed = []
            else:
                needed = []

            for field in needed:
                q = field_question(field)
                questions.append(q)
                events.append(Event(step="planner", message=f"Asked: {q}"))

            if block == "policy_check":
                questions.extend(policy_questions)
                for q in policy_questions:
                    events.append(Event(step="monitor", message=f"Asked: {q}"))

    elif strategy == "parallel":
        needed = missing_fields(plan, required_fields_for_blocks(blocks))
        for field in needed:
            q = field_question(field)
            questions.append(q)
            events.append(Event(step="planner", message=f"Asked upfront: {q}"))
        questions.extend(policy_questions)
        for q in policy_questions:
            events.append(Event(step="monitor", message=f"Asked upfront: {q}"))

    elif strategy == "routed":
        needed = missing_fields(plan, ["destination", "budget"])
        for field in needed:
            q = field_question(field)
            questions.append(q)
            events.append(Event(step="planner", message=f"Asked route-critical field: {q}"))

        questions.extend(policy_questions)
        for q in policy_questions:
            events.append(Event(step="monitor", message=f"Asked policy field: {q}"))

        route, route_reason, estimated_total, quote_components = routed_route_decision(
            plan,
            policy,
            blocks,
            manual_quotes,
        )
        if estimated_total:
            events.append(Event(step="monitor", message=f"Estimated quote total: {estimated_total}"))
            events.append(Event(step="monitor", message=f"Quote components: {quote_components}"))
        events.append(Event(step="router", message=f"Selected route: {route} ({route_reason})"))

        if route == "approval":
            questions.append("Do you approve this booking plan? (approve/deny)")
            decision = (request.approval_decision or "pending").lower()
            events.append(Event(step="approval_gate", message=f"Decision: {decision}"))
            if decision == "approve":
                missing_after_approval = missing_fields(plan, ["month", "travelers"])
                for field in missing_after_approval:
                    q = field_question(field)
                    questions.append(q)
                    events.append(Event(step="planner", message=f"Asked after approval: {q}"))
                route = "approved"
            elif decision == "deny":
                route = "denied"

    else:
        return {
            "error": "Unknown strategy. Use sequential, parallel, or routed.",
        }

    base_route = ""
    if strategy != "routed":
        base_route = route_for_plan(plan, policy)
        route_reason = "Budget/policy route from intent thresholds."
        decision = (request.approval_decision or "").lower()

        if base_route == "approval" and decision == "approve":
            route = "approved"
        elif base_route == "approval" and decision == "deny":
            route = "denied"
        else:
            route = base_route

    if strategy == "routed":
        visited_blocks = visited_blocks_for_routed(blocks, route, route_reason, request.approval_decision)
    else:
        if base_route == "approval" and route == "approved" and "approval_gate" in blocks:
            idx = blocks.index("approval_gate")
            visited_blocks = [b for b in blocks[idx + 1 :] if b != "blocked_end"]
        else:
            visited_blocks = visited_blocks_for_route(blocks, route)

    block_results = build_block_results(
        plan=plan,
        policy=policy,
        route=route,
        route_reason=route_reason,
        visited_blocks=visited_blocks,
        quote_components=quote_components,
        estimated_total=estimated_total,
        approval_decision=(request.approval_decision or None),
        manual_quote_keys=set(manual_quotes.keys()),
    )

    for block_id in visited_blocks:
        events.append(Event(step="flow", message=f"Entered block: {block_id}"))

    if route == "approved":
        events.append(Event(step="executor", message="Would execute selected booking blocks now."))
    elif route == "approval":
        events.append(Event(step="executor", message="Paused pending human approval."))
    elif route == "blocked":
        events.append(Event(step="executor", message="Stopped by hard policy limit."))
    elif route == "denied":
        events.append(Event(step="executor", message="Execution denied by human reviewer."))

    payload = {
        "strategy": strategy,
        "route": route,
        "route_reason": route_reason,
        "blocks": blocks,
        "plan": asdict(plan),
        "policy": asdict(policy),
        "estimated_total": estimated_total,
        "quote_components": quote_components,
        "block_results": block_results,
        "questions": questions,
        "events": [asdict(e) for e in events],
    }

    if route == "approved":
        payload["execution_outcome"] = "booking_executed"
        payload["itinerary"] = build_itinerary(plan, quote_components, estimated_total)
    elif route == "approval":
        payload["execution_outcome"] = "awaiting_human_approval"
        payload["itinerary"] = None
    elif route == "denied":
        payload["execution_outcome"] = "denied_no_execution"
        payload["itinerary"] = None
    elif route == "blocked":
        payload["execution_outcome"] = "blocked_no_execution"
        payload["itinerary"] = None
    else:
        payload["execution_outcome"] = "no_execution"
        payload["itinerary"] = None

    payload["narration"] = (
        "Ollama intent parsing enabled. "
        f"Parsed destination={plan.destination or 'missing'}, budget={plan.budget or 'missing'}, "
        f"month={plan.month or 'missing'}, travelers={plan.travelers or 'missing'}."
    )
    return payload


app = FastAPI(title="Orchestration Workbench")

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.post("/api/simulate")
def simulate_api(request: SimulationRequest) -> dict:
    return simulate(request)


@app.websocket("/ws/simulate")
async def simulate_ws(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        raw = await websocket.receive_text()
        request = SimulationRequest.model_validate_json(raw)

        plan = parse_prompt(request.prompt)
        policy, _ = parse_policy(request.prompt, request.approval_limit, request.blocked_limit)
        estimated_total = 0
        components: dict[str, int] = {}
        manual_quotes = {
            "flight_search": request.flight_quote,
            "hotel_search": request.hotel_quote,
            "insurance_quote": request.insurance_quote,
        }
        manual_quotes = {k: v for k, v in manual_quotes.items() if v is not None and v >= 0}
        estimated_total, components = estimate_quote_total(plan, request.blocks, manual_quotes)

        if request.strategy.lower() == "routed":
            route, route_reason, estimated_total, components = routed_route_decision(
                plan,
                policy,
                request.blocks,
                manual_quotes,
            )
            if route == "approval" and (request.approval_decision or "").lower() == "deny":
                route = "denied"
            if route == "approval" and (request.approval_decision or "").lower() == "approve":
                route = "approved"
            visited_blocks = visited_blocks_for_routed(request.blocks, route, route_reason, request.approval_decision)
        else:
            base_route = route_for_plan(plan, policy)
            route_reason = "Budget/policy route from intent thresholds."
            decision = (request.approval_decision or "").lower()

            if base_route == "approval" and decision == "approve":
                route = "approved"
            elif base_route == "approval" and decision == "deny":
                route = "denied"
            else:
                route = base_route

            if base_route == "approval" and route == "approved" and "approval_gate" in request.blocks:
                idx = request.blocks.index("approval_gate")
                visited_blocks = [b for b in request.blocks[idx + 1 :] if b != "blocked_end"]
            else:
                visited_blocks = visited_blocks_for_route(request.blocks, route)

        block_results = build_block_results(
            plan=plan,
            policy=policy,
            route=route,
            route_reason=route_reason,
            visited_blocks=visited_blocks,
            quote_components=components,
            estimated_total=estimated_total,
            approval_decision=(request.approval_decision or None),
            manual_quote_keys=set(manual_quotes.keys()),
        )

        block_result_map = {item["block"]: item for item in block_results}

        await websocket.send_json({"type": "run_started", "route": route})

        for block_id in visited_blocks:
            await websocket.send_json(
                {
                    "type": "step",
                    "block": block_id,
                    "block_result": block_result_map.get(block_id),
                }
            )
            await asyncio.sleep(0.35)

        if route == "approval" and not request.approval_decision:
            approval_index = request.blocks.index("approval_gate") if "approval_gate" in request.blocks else len(request.blocks)
            will_run = request.blocks[approval_index + 1 :] if approval_index < len(request.blocks) else []

            await websocket.send_json(
                {
                    "type": "awaiting_approval",
                    "route": route,
                    "block_results": block_results,
                    "approval_context": {
                        "reason": route_reason,
                        "budget": plan.budget,
                        "approval_limit": policy.approval_limit,
                        "blocked_limit": policy.blocked_limit,
                        "estimated_total": estimated_total,
                        "quote_components": components,
                        "will_run_blocks": will_run,
                    },
                }
            )
            await websocket.close()
            return

        await websocket.send_json(
            {
                "type": "finalizing",
                "message": "Generating final run summary and narration.",
            }
        )

        result = simulate(request)
        await websocket.send_json({"type": "result", "payload": result})
        await websocket.close()
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close()
