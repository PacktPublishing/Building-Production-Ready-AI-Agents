from dataclasses import dataclass


@dataclass(frozen=True)
class CanarySignals:
    runs: int
    window_minutes: int
    completion_rate: float
    policy_denied_rate: float
    p95_latency_seconds: float
    cost_per_success: float


@dataclass(frozen=True)
class RolloutLimits:
    minimum_runs: int = 100
    evaluation_window_minutes: int = 60
    maximum_completion_drop: float = 0.02
    completion_slo: float = 0.92
    maximum_error_budget_burn: float = 1.0
    maximum_policy_denied_rate: float = 0.05
    maximum_p95_latency_seconds: float = 8.0
    maximum_cost_per_success: float = 0.12


def stopping_reasons(
    control: CanarySignals,
    candidate: CanarySignals,
    limits: RolloutLimits,
) -> list[str]:
    reasons: list[str] = []
    if candidate.runs < limits.minimum_runs:
        reasons.append("minimum_runs")
    if candidate.window_minutes < limits.evaluation_window_minutes:
        reasons.append("evaluation_window")
    if candidate.completion_rate < control.completion_rate - limits.maximum_completion_drop:
        reasons.append("completion_rate")
    if completion_error_budget_burn(candidate, limits) > limits.maximum_error_budget_burn:
        reasons.append("completion_error_budget")
    if candidate.policy_denied_rate > limits.maximum_policy_denied_rate:
        reasons.append("policy_denied_rate")
    if candidate.p95_latency_seconds > limits.maximum_p95_latency_seconds:
        reasons.append("p95_latency")
    if candidate.cost_per_success > limits.maximum_cost_per_success:
        reasons.append("cost_per_success")
    return reasons


def completion_error_budget_burn(
    candidate: CanarySignals, limits: RolloutLimits
) -> float:
    allowed_incomplete_rate = 1.0 - limits.completion_slo
    observed_incomplete_rate = 1.0 - candidate.completion_rate
    return observed_incomplete_rate / allowed_incomplete_rate


def rollout_action(reasons: list[str]) -> str:
    if not reasons:
        return "advance"
    evidence_reasons = {"minimum_runs", "evaluation_window"}
    if set(reasons).issubset(evidence_reasons):
        return "hold"
    return "rollback_and_investigate"


def main() -> None:
    limits = RolloutLimits()
    control = CanarySignals(1000, 60, 0.94, 0.02, 6.4, 0.08)
    healthy_candidate = CanarySignals(200, 60, 0.93, 0.03, 7.2, 0.09)
    slow_candidate = CanarySignals(200, 60, 0.93, 0.03, 8.6, 0.09)

    healthy_reasons = stopping_reasons(control, healthy_candidate, limits)
    slow_reasons = stopping_reasons(control, slow_candidate, limits)
    budget_burn = completion_error_budget_burn(healthy_candidate, limits)

    assert healthy_reasons == []
    assert slow_reasons == ["p95_latency"]
    assert round(budget_burn, 3) == 0.875

    print(f"Completion error-budget burn: {budget_burn:.1%}")
    print(f"Healthy canary action: {rollout_action(healthy_reasons)}")
    print(f"Slow canary action: {rollout_action(slow_reasons)}")
    print(f"Stopping reasons: {slow_reasons}")


if __name__ == "__main__":
    main()