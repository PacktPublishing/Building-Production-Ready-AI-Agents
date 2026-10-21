from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from typing import Any

from ollama import Client


@dataclass
class TravelPlan:
    destination: str
    budget: int
    month: str
    travelers: int


@dataclass
class PolicyDecision:
    status: str
    reason: str


@dataclass
class PolicyConfig:
    approval_limit: int
    blocked_limit: int


class Colors:
    RESET = "\033[0m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    MAGENTA = "\033[35m"


def colorize(text: str, color: str) -> str:
    if os.getenv("NO_COLOR"):
        return text
    return f"{color}{text}{Colors.RESET}"


def heading(label: str) -> None:
    print(colorize(f"\n== {label} ==", Colors.MAGENTA))


def step(label: str, message: str) -> None:
    print(colorize(f"[{label}] {message}", Colors.CYAN))


def outcome(message: str) -> None:
    print(colorize(message, Colors.GREEN))


class OllamaNarrator:
    def __init__(self) -> None:
        self.host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
        self.client = Client(host=self.host)

    def summarize(self, pattern: str, payload: dict[str, Any]) -> str:
        system_prompt = (
            "You are a concise instructor narrating an orchestration demo. "
            "Explain what happened in 4-6 short bullet points. "
            "Keep the explanation concrete and tied to control flow."
        )
        user_prompt = (
            f"Pattern: {pattern}\n"
            f"Payload: {json.dumps(payload, indent=2)}\n"
            "Summarize the run for a beginner learning orchestration patterns."
        )
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response["message"]["content"].strip()
        except Exception:
            return self._fallback(pattern, payload)

    def _fallback(self, pattern: str, payload: dict[str, Any]) -> str:
        return "\n".join(
            [
                f"- Pattern used: {pattern}",
                f"- Destination: {payload['plan']['destination']}",
                f"- Budget: {payload['plan']['budget']}",
                f"- Policy result: {payload['policy']['status']} ({payload['policy']['reason']})",
                f"- Final outcome: {payload['result']}",
            ]
        )


def parse_policy_config(
    user_request: str,
    approval_limit_override: int | None = None,
    blocked_limit_override: int | None = None,
) -> PolicyConfig:
    default_approval = 1200
    default_blocked = 2000

    approval_match = re.search(
        r"(?:approval\s*limit|approval\s*above|approve\s*up\s*to|autonomous\s*limit)\D*(\d{3,5})",
        user_request,
        re.IGNORECASE,
    )
    blocked_match = re.search(
        r"(?:block\s*limit|block\s*above|hard\s*limit|max\s*without\s*exception)\D*(\d{3,5})",
        user_request,
        re.IGNORECASE,
    )

    approval_limit = approval_limit_override or (
        int(approval_match.group(1)) if approval_match else default_approval
    )
    blocked_limit = blocked_limit_override or (
        int(blocked_match.group(1)) if blocked_match else default_blocked
    )

    if blocked_limit <= approval_limit:
        blocked_limit = approval_limit + 1

    return PolicyConfig(approval_limit=approval_limit, blocked_limit=blocked_limit)


def resolve_policy_config_with_followups(
    user_request: str,
    approval_limit_override: int | None = None,
    blocked_limit_override: int | None = None,
    prompt_for_missing_limits: bool = False,
) -> tuple[PolicyConfig, list[str]]:
    follow_ups: list[str] = []
    config = parse_policy_config(
        user_request,
        approval_limit_override,
        blocked_limit_override,
    )

    if not prompt_for_missing_limits:
        return config, follow_ups

    has_approval_in_request = bool(
        re.search(
            r"(?:approval\s*limit|approval\s*above|approve\s*up\s*to|autonomous\s*limit)\D*(\d{3,5})",
            user_request,
            re.IGNORECASE,
        )
    )
    has_blocked_in_request = bool(
        re.search(
            r"(?:block\s*limit|block\s*above|hard\s*limit|max\s*without\s*exception)\D*(\d{3,5})",
            user_request,
            re.IGNORECASE,
        )
    )

    should_ask_approval = approval_limit_override is None and not has_approval_in_request
    should_ask_blocked = blocked_limit_override is None and not has_blocked_in_request

    if not sys.stdin.isatty():
        if should_ask_approval:
            follow_ups.append("Approval limit not provided; using default policy limit.")
        if should_ask_blocked:
            follow_ups.append("Blocked limit not provided; using default policy limit.")
        return config, follow_ups

    if should_ask_approval:
        follow_ups.append("Asked for approval-limit threshold.")
        config.approval_limit = int(
            _prompt_with_default(
                "Approval limit (budget above this requires approval)",
                str(config.approval_limit),
            )
        )

    if should_ask_blocked:
        follow_ups.append("Asked for blocked-limit threshold.")
        config.blocked_limit = int(
            _prompt_with_default(
                "Blocked limit (budget above this blocks execution)",
                str(config.blocked_limit),
            )
        )

    if config.blocked_limit <= config.approval_limit:
        config.blocked_limit = config.approval_limit + 1
        follow_ups.append("Adjusted blocked limit so it stays above approval limit.")

    return config, follow_ups


def ask_human_approval(prompt: str, default: bool = False) -> bool:
    if not sys.stdin.isatty():
        return default

    default_hint = "Y/n" if default else "y/N"
    try:
        raw = input(f"{prompt} [{default_hint}]: ").strip().lower()
    except EOFError:
        return default

    if not raw:
        return default
    return raw in {"y", "yes"}


def _prompt_with_default(prompt: str, default: str) -> str:
    try:
        value = input(f"{prompt} [{default}]: ").strip()
        return value or default
    except EOFError:
        return default


def parse_request(user_request: str) -> tuple[TravelPlan, list[str]]:
    destination_match = re.search(r"to\s+([A-Za-z ]+?)(?:\s+next|\s+in|\s+with|$)", user_request, re.IGNORECASE)
    budget_match = re.search(r"(?:budget\D*)?(\d{3,5})", user_request, re.IGNORECASE)
    month_match = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december|next month)", user_request, re.IGNORECASE)
    traveler_match = re.search(r"(\d+)\s+(?:traveler|travelers|people|person)", user_request, re.IGNORECASE)

    follow_ups: list[str] = []

    if destination_match:
        destination = destination_match.group(1).strip().title()
    else:
        follow_ups.append("Missing destination in request.")
        destination = _prompt_with_default("Destination city", "Berlin").title()

    if budget_match:
        budget = int(budget_match.group(1))
    else:
        follow_ups.append("Missing budget in request.")
        budget = int(_prompt_with_default("Budget in dollars", "1200"))

    if month_match:
        month = month_match.group(1).lower()
    else:
        follow_ups.append("Missing travel month in request.")
        month = _prompt_with_default("Month", "next month").lower()

    if traveler_match:
        travelers = int(traveler_match.group(1))
    else:
        follow_ups.append("Missing traveler count in request.")
        travelers = int(_prompt_with_default("Number of travelers", "1"))

    return (
        TravelPlan(
            destination=destination,
            budget=budget,
            month=month,
            travelers=travelers,
        ),
        follow_ups,
    )


def check_policy(plan: TravelPlan, config: PolicyConfig) -> PolicyDecision:
    if plan.budget > config.blocked_limit:
        return PolicyDecision(status="blocked", reason="budget above automatic booking limit")
    if plan.budget > config.approval_limit:
        return PolicyDecision(status="approval", reason="budget requires human approval")
    return PolicyDecision(status="approved", reason="budget is within autonomous limit")


def fetch_flight_options(plan: TravelPlan) -> list[str]:
    return [
        f"Flight A to {plan.destination} for ${int(plan.budget * 0.45)}",
        f"Flight B to {plan.destination} for ${int(plan.budget * 0.5)}",
    ]


def fetch_hotel_options(plan: TravelPlan) -> list[str]:
    return [
        f"Hotel Central in {plan.destination} for ${int(plan.budget * 0.3)}",
        f"Hotel Riverside in {plan.destination} for ${int(plan.budget * 0.35)}",
    ]


def fetch_insurance_options(plan: TravelPlan) -> list[str]:
    return [
        f"Standard insurance for ${max(40, int(plan.budget * 0.05))}",
        f"Flexible insurance for ${max(70, int(plan.budget * 0.08))}",
    ]


async def fetch_flight_options_async(plan: TravelPlan) -> list[str]:
    await asyncio.sleep(0.1)
    return fetch_flight_options(plan)


async def fetch_hotel_options_async(plan: TravelPlan) -> list[str]:
    await asyncio.sleep(0.1)
    return fetch_hotel_options(plan)


async def fetch_insurance_options_async(plan: TravelPlan) -> list[str]:
    await asyncio.sleep(0.1)
    return fetch_insurance_options(plan)


def execute_booking(plan: TravelPlan, options: dict[str, list[str]]) -> str:
    return (
        f"Booked {plan.destination} for {plan.travelers} traveler(s) in {plan.month}. "
        f"Chosen flight: {options['flights'][0]}; hotel: {options['hotels'][0]}."
    )


def default_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--request",
        default="Book a trip to Berlin next month with a budget of 900 dollars",
        help="Natural-language travel request used as the starting point.",
    )
    parser.add_argument(
        "--approval-limit",
        type=int,
        default=None,
        help="Optional budget threshold above which approval is required.",
    )
    parser.add_argument(
        "--blocked-limit",
        type=int,
        default=None,
        help="Optional budget threshold above which execution is blocked.",
    )
    return parser


def payload_for_summary(
    plan: TravelPlan,
    policy: PolicyDecision,
    result: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "plan": asdict(plan),
        "policy": asdict(policy),
        "result": result,
    }
    if extra:
        payload.update(extra)
    return payload