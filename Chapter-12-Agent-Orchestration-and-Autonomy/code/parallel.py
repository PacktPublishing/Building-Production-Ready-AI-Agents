from __future__ import annotations

import asyncio

from common import (
    OllamaNarrator,
    check_policy,
    default_parser,
    execute_booking,
    fetch_flight_options_async,
    fetch_hotel_options_async,
    fetch_insurance_options_async,
    heading,
    outcome,
    parse_policy_config,
    parse_request,
    payload_for_summary,
    step,
)


async def run() -> None:
    parser = default_parser("Parallel orchestration demo")
    args = parser.parse_args()

    narrator = OllamaNarrator()
    plan, follow_ups = parse_request(args.request)
    policy_config = parse_policy_config(
        args.request,
        args.approval_limit,
        args.blocked_limit,
    )

    heading("Parallel orchestration")
    step("PLANNER", f"Collected plan: {plan}")
    if follow_ups:
        step("PLANNER", f"Follow-up questions asked: {len(follow_ups)}")

    policy = check_policy(plan, policy_config)
    step("MONITOR", f"Policy decision: {policy.status} ({policy.reason})")

    if policy.status != "approved":
        result = f"Workflow stopped before concurrent work began: {policy.reason}."
        step("ORCHESTRATOR", result)
    else:
        step("ORCHESTRATOR", "Gathering flights, hotels, and insurance in parallel")
        flights, hotels, insurance = await asyncio.gather(
            fetch_flight_options_async(plan),
            fetch_hotel_options_async(plan),
            fetch_insurance_options_async(plan),
        )
        result = execute_booking(
            plan,
            {"flights": flights, "hotels": hotels, "insurance": insurance},
        )
        step("EXECUTOR", result)

    summary = narrator.summarize(
        "parallel",
        payload_for_summary(
            plan,
            policy,
            result,
            {"execution_style": "Independent I/O-style lookups are awaited as one batch."},
        ),
    )
    heading("Summary")
    outcome(summary)


if __name__ == "__main__":
    asyncio.run(run())