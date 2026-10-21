"""Exercise 3 solution: deterministic conflict resolution.

Run:
    python solutions/exercise-3-conflict-handling.py
"""

from __future__ import annotations


def resolve_conflict(plan: dict, research: dict, policy: dict) -> dict:
    """Resolve competing recommendations using deterministic precedence rules."""
    if not plan or not plan.get("destination"):
        return {"decision": "revise", "reason": "incomplete plan structure"}

    if not policy.get("approved"):
        return {"decision": "revise", "reason": "policy block"}

    if research.get("confidence", 0) < 0.7:
        return {"decision": "revise", "reason": "research too weak"}

    return {"decision": "accept", "reason": "plan is consistent"}


def run_case(name: str, plan: dict, research: dict, policy: dict) -> None:
    result = resolve_conflict(plan, research, policy)
    print(f"{name}: {result['decision']} ({result['reason']})")


def main() -> None:
    print("Conflict resolution outcomes")
    print("----------------------------")

    run_case(
        "Case 1 - Incomplete plan",
        plan={"hotel": "B"},
        research={"confidence": 0.95},
        policy={"approved": True},
    )

    run_case(
        "Case 2 - Policy blocks",
        plan={"destination": "Copenhagen", "hotel": "B"},
        research={"confidence": 0.95},
        policy={"approved": False},
    )

    run_case(
        "Case 3 - Low confidence",
        plan={"destination": "Copenhagen", "hotel": "B"},
        research={"confidence": 0.55},
        policy={"approved": True},
    )

    run_case(
        "Case 4 - Accepted",
        plan={"destination": "Copenhagen", "hotel": "B"},
        research={"confidence": 0.9},
        policy={"approved": True},
    )


if __name__ == "__main__":
    main()
