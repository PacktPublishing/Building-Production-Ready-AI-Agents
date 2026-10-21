from __future__ import annotations

from common import (
    OllamaNarrator,
    check_policy,
    default_parser,
    execute_booking,
    fetch_flight_options,
    fetch_hotel_options,
    fetch_insurance_options,
    heading,
    outcome,
    parse_policy_config,
    parse_request,
    payload_for_summary,
    step,
)


def main() -> None:
    parser = default_parser("Sequential orchestration demo")
    args = parser.parse_args()

    narrator = OllamaNarrator()
    plan, follow_ups = parse_request(args.request)
    policy_config = parse_policy_config(
        args.request,
        args.approval_limit,
        args.blocked_limit,
    )

    heading("Sequential orchestration")
    step("PLANNER", f"Collected plan: {plan}")
    if follow_ups:
        step("PLANNER", f"Follow-up questions asked: {len(follow_ups)}")

    policy = check_policy(plan, policy_config)
    step("MONITOR", f"Policy decision: {policy.status} ({policy.reason})")

    if policy.status != "approved":
        result = f"Workflow stopped before execution: {policy.reason}."
        step("ORCHESTRATOR", result)
    else:
        step("EXECUTOR", "Fetching flights")
        flights = fetch_flight_options(plan)
        step("EXECUTOR", "Fetching hotels")
        hotels = fetch_hotel_options(plan)
        step("EXECUTOR", "Fetching insurance")
        insurance = fetch_insurance_options(plan)
        result = execute_booking(
            plan,
            {"flights": flights, "hotels": hotels, "insurance": insurance},
        )
        step("EXECUTOR", result)

    summary = narrator.summarize(
        "sequential",
        payload_for_summary(
            plan,
            policy,
            result,
            {"execution_style": "Each dependency is resolved one after another."},
        ),
    )
    heading("Summary")
    outcome(summary)


if __name__ == "__main__":
    main()