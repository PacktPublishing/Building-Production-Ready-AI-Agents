from __future__ import annotations

from common import (
    ask_human_approval,
    OllamaNarrator,
    check_policy,
    default_parser,
    execute_booking,
    fetch_flight_options,
    fetch_hotel_options,
    fetch_insurance_options,
    heading,
    outcome,
    parse_request,
    payload_for_summary,
    resolve_policy_config_with_followups,
    step,
)


def main() -> None:
    parser = default_parser("Routed orchestration demo")
    parser.add_argument(
        "--approval-decision",
        choices=["approve", "deny"],
        default=None,
        help="Optional explicit approval decision for routed approval branch.",
    )
    args = parser.parse_args()

    narrator = OllamaNarrator()
    plan, follow_ups = parse_request(args.request)
    policy_config, policy_follow_ups = resolve_policy_config_with_followups(
        args.request,
        args.approval_limit,
        args.blocked_limit,
        prompt_for_missing_limits=True,
    )

    heading("Routed orchestration")
    step("PLANNER", f"Collected plan: {plan}")
    if follow_ups:
        step("PLANNER", f"Follow-up questions asked: {len(follow_ups)}")
    if policy_follow_ups:
        step("MONITOR", f"Policy follow-ups asked: {len(policy_follow_ups)}")
    step(
        "MONITOR",
        (
            "Policy limits in use: "
            f"approval_limit={policy_config.approval_limit}, "
            f"blocked_limit={policy_config.blocked_limit}"
        ),
    )

    policy = check_policy(plan, policy_config)
    step("MONITOR", f"Policy decision: {policy.status} ({policy.reason})")

    route_taken = policy.status

    if policy.status == "blocked":
        result = "Run stopped. The user must lower the budget before any booking work can continue."
        step("ROUTER", "Selected blocked branch")
    elif policy.status == "approval":
        step("ROUTER", "Selected approval branch")
        if args.approval_decision is not None:
            approved = args.approval_decision == "approve"
            step("HITL", f"Approval decision from CLI: {args.approval_decision}")
        else:
            approved = ask_human_approval(
                "Budget requires approval. Continue to booking execution?",
                default=False,
            )
            step("HITL", f"Interactive approval decision: {'approved' if approved else 'denied'}")

        if approved:
            route_taken = "approval_approved"
            step("ROUTER", "Approval granted, continuing to execution")
            flights = fetch_flight_options(plan)
            hotels = fetch_hotel_options(plan)
            insurance = fetch_insurance_options(plan)
            result = execute_booking(
                plan,
                {"flights": flights, "hotels": hotels, "insurance": insurance},
            )
            step("EXECUTOR", result)
        else:
            route_taken = "approval_denied"
            result = "Run paused/stopped because approval was not granted."
            step("ROUTER", "Approval denied, execution not started")
    else:
        step("ROUTER", "Selected autonomous execution branch")
        flights = fetch_flight_options(plan)
        hotels = fetch_hotel_options(plan)
        insurance = fetch_insurance_options(plan)
        result = execute_booking(
            plan,
            {"flights": flights, "hotels": hotels, "insurance": insurance},
        )
        step("EXECUTOR", result)

    summary = narrator.summarize(
        "routed",
        payload_for_summary(
            plan,
            policy,
            result,
            {
                "route_taken": route_taken,
                "policy_limits": {
                    "approval_limit": policy_config.approval_limit,
                    "blocked_limit": policy_config.blocked_limit,
                },
                "plan_follow_ups": follow_ups,
                "policy_follow_ups": policy_follow_ups,
            },
        ),
    )
    heading("Summary")
    outcome(summary)


if __name__ == "__main__":
    main()