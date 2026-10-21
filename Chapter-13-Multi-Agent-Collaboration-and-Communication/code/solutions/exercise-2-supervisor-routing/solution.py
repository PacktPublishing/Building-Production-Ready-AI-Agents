"""Exercise 2 solution: supervisor routing with explicit message envelopes.

Run:
    python solutions/exercise-2-supervisor-routing/solution.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    trace_id: str
    from_agent: str
    to_agent: str
    type: str
    payload: dict[str, Any]


def validate_message(message: Message) -> None:
    if not message.trace_id:
        raise ValueError("trace_id is required")
    if not message.from_agent:
        raise ValueError("from_agent is required")
    if not message.to_agent:
        raise ValueError("to_agent is required")
    if not message.type:
        raise ValueError("type is required")
    if not isinstance(message.payload, dict):
        raise ValueError("payload must be a dictionary")


def dispatch_next_agent(message: Message) -> str:
    if message.type == "request" and message.to_agent == "researcher":
        return "researcher"
    if message.type == "plan_review" and message.to_agent == "policy":
        return "policy"
    if message.type == "revise" and message.to_agent == "planner":
        return "planner"
    if message.type == "ack" and message.to_agent == "coordinator":
        return "coordinator"
    return "human reviewer"


def main() -> None:
    inbox = [
        Message(
            trace_id="trip-2048",
            from_agent="planner",
            to_agent="researcher",
            type="request",
            payload={"goal": "book Copenhagen trip", "constraints": ["budget < 2200"]},
        ),
        Message(
            trace_id="trip-2048",
            from_agent="researcher",
            to_agent="policy",
            type="plan_review",
            payload={"quoted_total": 1975},
        ),
        Message(
            trace_id="trip-2048",
            from_agent="policy",
            to_agent="planner",
            type="revise",
            payload={"reason": "missing refundable option"},
        ),
    ]

    print("Exercise 2: supervisor routing")
    print("--------------------------------")
    print("Input: three hard-coded messages in one trace_id (trip-2048)")
    print("Output: one line per message showing the chosen next agent")
    print("Can change: the next agent changes if type or to_agent changes")
    print()
    for message in inbox:
        validate_message(message)
        next_agent = dispatch_next_agent(message)
        print(f"input: {message}")
        print(
            f"{message.trace_id} | {message.from_agent} -> {message.to_agent} "
            f"({message.type}) => next: {next_agent}"
        )
        print()


if __name__ == "__main__":
    main()
