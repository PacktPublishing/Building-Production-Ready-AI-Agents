from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


TERMINAL_EVENT_TYPES = frozenset({"run_completed", "run_stopped"})


@dataclass(frozen=True)
class CohortStats:
    eligible: int
    incomplete: int
    quarantined: int
    max_steps: int

    @property
    def max_steps_rate(self) -> float:
        return self.max_steps / self.eligible if self.eligible else 0.0


def canonical_terminal(event: Mapping[str, Any]) -> str | None:
    event_type = event.get("event_type")
    if event_type == "run_completed":
        return "completed"
    if event_type == "run_stopped":
        reason = event.get("reason")
        if not isinstance(reason, str) or not reason:
            raise ValueError("run_stopped requires a non-empty reason")
        return reason
    return None


def project_terminal_cohorts(
    events: Iterable[Mapping[str, Any]],
) -> dict[str, CohortStats]:
    outcomes_by_run: dict[tuple[str, str], set[str]] = defaultdict(set)
    seen_runs: set[tuple[str, str]] = set()

    for event in events:
        prompt_version = event.get("prompt_version")
        run_id = event.get("run_id")
        if not isinstance(prompt_version, str) or not isinstance(run_id, str):
            raise ValueError("every event requires prompt_version and run_id")
        key = (prompt_version, run_id)
        seen_runs.add(key)
        outcome = canonical_terminal(event)
        if outcome is not None:
            outcomes_by_run[key].add(outcome)

    totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "eligible": 0,
            "incomplete": 0,
            "quarantined": 0,
            "max_steps": 0,
        }
    )
    for prompt_version, run_id in seen_runs:
        outcomes = outcomes_by_run[(prompt_version, run_id)]
        if not outcomes:
            totals[prompt_version]["incomplete"] += 1
        elif len(outcomes) > 1:
            totals[prompt_version]["quarantined"] += 1
        else:
            outcome = next(iter(outcomes))
            totals[prompt_version]["eligible"] += 1
            if outcome == "max_steps":
                totals[prompt_version]["max_steps"] += 1

    return {
        prompt_version: CohortStats(**counts)
        for prompt_version, counts in totals.items()
    }


def build_springfield_fixture() -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    fixture = {
        "v12": {"eligible": 100, "max_steps": 1, "incomplete": 2},
        "v13": {"eligible": 100, "max_steps": 8, "incomplete": 5},
    }
    for version, counts in fixture.items():
        for index in range(counts["eligible"]):
            run_id = f"springfield-{version}-{index:03d}"
            events.append(
                {
                    "prompt_version": version,
                    "run_id": run_id,
                    "event_type": "run_started",
                }
            )
            if index < counts["max_steps"]:
                events.append(
                    {
                        "prompt_version": version,
                        "run_id": run_id,
                        "event_type": "run_stopped",
                        "reason": "max_steps",
                    }
                )
            else:
                events.append(
                    {
                        "prompt_version": version,
                        "run_id": run_id,
                        "event_type": "run_completed",
                    }
                )

        for index in range(counts["incomplete"]):
            events.append(
                {
                    "prompt_version": version,
                    "run_id": f"springfield-{version}-incomplete-{index}",
                    "event_type": "run_started",
                }
            )

        conflict_id = f"springfield-{version}-conflict"
        events.extend(
            [
                {
                    "prompt_version": version,
                    "run_id": conflict_id,
                    "event_type": "run_completed",
                },
                {
                    "prompt_version": version,
                    "run_id": conflict_id,
                    "event_type": "run_stopped",
                    "reason": "max_steps",
                },
            ]
        )

    events.append(
        {
            "prompt_version": "v13",
            "run_id": "springfield-v13-000",
            "event_type": "run_stopped",
            "reason": "max_steps",
        }
    )
    return events


def leading_hypothesis(
    old: CohortStats,
    new: CohortStats,
    changed_components: Iterable[str],
    minimum_eligible: int = 100,
) -> str:
    changed = set(changed_components)
    if (
        changed == {"prompt"}
        and old.eligible >= minimum_eligible
        and new.eligible >= minimum_eligible
        and new.max_steps_rate > old.max_steps_rate
    ):
        return "prompt"
    return "undetermined"


def _event_type(event: str | Mapping[str, Any]) -> str:
    return event if isinstance(event, str) else str(event.get("event_type", ""))


def validate_regression(
    trajectory: Sequence[str | Mapping[str, Any]],
    scenario: Mapping[str, Any],
    actual_termination: str,
) -> bool:
    event_types = [_event_type(event) for event in trajectory]
    expected_events = list(scenario["expected_events"])
    expected_position = 0
    for event_type in event_types:
        if (
            expected_position < len(expected_events)
            and event_type == expected_events[expected_position]
        ):
            expected_position += 1
    if expected_position != len(expected_events):
        return False
    if set(event_types).intersection(scenario["forbidden_events"]):
        return False

    terminal_events = [
        event for event in trajectory if _event_type(event) in TERMINAL_EVENT_TYPES
    ]
    if len(terminal_events) != 1:
        return False
    terminal_event = terminal_events[0]
    if isinstance(terminal_event, str):
        event_termination = "completed" if terminal_event == "run_completed" else None
    else:
        event_termination = canonical_terminal(terminal_event)
    return (
        event_termination == actual_termination
        and actual_termination == scenario["expected_termination"]
    )


@dataclass(frozen=True)
class CanarySignals:
    window_minutes: int
    eligible_runs: int
    completion_rate: float
    policy_denial_rate: float
    p95_latency_seconds: float
    cost_per_success: float

    def __post_init__(self) -> None:
        if self.window_minutes < 0 or self.eligible_runs < 0:
            raise ValueError("window and eligible runs cannot be negative")
        for name in ("completion_rate", "policy_denial_rate"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.p95_latency_seconds < 0 or self.cost_per_success < 0:
            raise ValueError("latency and cost cannot be negative")


@dataclass(frozen=True)
class RolloutLimits:
    minimum_window_minutes: int = 60
    minimum_eligible_runs: int = 100
    completion_slo: float = 0.92
    maximum_completion_budget_consumption: float = 1.0
    maximum_relative_completion_drop: float = 0.05
    maximum_policy_denial_rate: float = 0.05
    maximum_p95_latency_seconds: float = 8.0
    maximum_cost_per_success: float = 0.12

    def __post_init__(self) -> None:
        if self.minimum_window_minutes < 1 or self.minimum_eligible_runs < 1:
            raise ValueError("minimum window and eligible runs must be positive")
        for name in (
            "completion_slo",
            "maximum_relative_completion_drop",
            "maximum_policy_denial_rate",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if (
            self.maximum_completion_budget_consumption < 0
            or self.maximum_p95_latency_seconds < 0
            or self.maximum_cost_per_success < 0
        ):
            raise ValueError("rollout limits cannot be negative")


def completion_window_budget_consumption(
    signals: CanarySignals, limits: RolloutLimits
) -> float:
    allowed_incomplete_rate = 1.0 - limits.completion_slo
    observed_incomplete_rate = 1.0 - signals.completion_rate
    if allowed_incomplete_rate == 0.0:
        return 0.0 if observed_incomplete_rate == 0.0 else math.inf
    return observed_incomplete_rate / allowed_incomplete_rate


def stopping_reasons(
    control: CanarySignals,
    candidate: CanarySignals,
    limits: RolloutLimits,
) -> list[str]:
    reasons: list[str] = []
    if candidate.window_minutes < limits.minimum_window_minutes:
        reasons.append("insufficient_window")
    if candidate.eligible_runs < limits.minimum_eligible_runs:
        reasons.append("insufficient_traffic")
    relative_drop = (
        (control.completion_rate - candidate.completion_rate) / control.completion_rate
        if control.completion_rate
        else 0.0
    )
    if relative_drop > limits.maximum_relative_completion_drop:
        reasons.append("completion_regression")
    if (
        completion_window_budget_consumption(candidate, limits)
        > limits.maximum_completion_budget_consumption
    ):
        reasons.append("completion_budget")
    if candidate.policy_denial_rate > limits.maximum_policy_denial_rate:
        reasons.append("policy_denials")
    if candidate.p95_latency_seconds > limits.maximum_p95_latency_seconds:
        reasons.append("p95_latency")
    if candidate.cost_per_success > limits.maximum_cost_per_success:
        reasons.append("cost_per_success")
    return reasons


def rollout_action(reasons: Sequence[str]) -> str:
    if not reasons:
        return "advance"
    if set(reasons).issubset({"insufficient_window", "insufficient_traffic"}):
        return "hold"
    return "rollback_and_investigate"


def build_investigation_artifact(
    action: str,
    reasons: Sequence[str],
    candidate_versions: Mapping[str, str],
    cohort: Mapping[str, Any],
    metrics: CanarySignals,
    limits: RolloutLimits,
    representative_trace_ids: Sequence[str],
    next_checks: Sequence[str],
) -> dict[str, Any]:
    return {
        "action": action,
        "reasons": list(reasons),
        "candidate_versions": dict(candidate_versions),
        "cohort": dict(cohort),
        "metrics": asdict(metrics),
        "limits": asdict(limits),
        "representative_trace_ids": list(representative_trace_ids),
        "next_checks": list(next_checks),
    }


def main() -> None:
    cohorts = project_terminal_cohorts(build_springfield_fixture())
    for version in ("v12", "v13"):
        cohort = cohorts[version]
        print(
            f"{version}: eligible={cohort.eligible} incomplete={cohort.incomplete} "
            f"quarantined={cohort.quarantined} max_steps={cohort.max_steps} "
            f"rate={cohort.max_steps_rate:.1%}"
        )
    print(
        "Leading hypothesis: "
        f"{leading_hypothesis(cohorts['v12'], cohorts['v13'], {'prompt'})}"
    )

    affected_scenario = {
        "expected_events": ["run_started", "tool_requested", "run_stopped"],
        "forbidden_events": ["unsafe_tool_executed"],
        "expected_termination": "max_steps",
    }
    affected = [
        "run_started",
        "model_requested",
        "tool_requested",
        {"event_type": "run_stopped", "reason": "max_steps"},
    ]
    corrected_scenario = {
        "expected_events": ["run_started", "tool_completed", "run_completed"],
        "forbidden_events": ["run_stopped"],
        "expected_termination": "completed",
    }
    corrected = ["run_started", "tool_completed", "run_completed"]
    print(
        "Affected scenario reproduced: "
        f"{validate_regression(affected, affected_scenario, 'max_steps')}"
    )
    print(
        "Corrected regression passes: "
        f"{validate_regression(corrected, corrected_scenario, 'completed')}"
    )
    print(
        "Wrong termination passes: "
        f"{validate_regression(corrected, corrected_scenario, 'max_steps')}"
    )

    control = CanarySignals(60, 100, 0.95, 0.01, 5.0, 0.08)
    candidate = CanarySignals(60, 100, 0.93, 0.02, 9.0, 0.09)
    limits = RolloutLimits()
    consumption = completion_window_budget_consumption(candidate, limits)
    reasons = stopping_reasons(control, candidate, limits)
    action = rollout_action(reasons)
    print(f"Completion window budget consumption: {consumption:.1%}")
    print(f"Stopping reasons: {', '.join(reasons)}")
    print(f"Canary action: {action}")

    artifact = build_investigation_artifact(
        action=action,
        reasons=reasons,
        candidate_versions={
            "agent": "travel-agent-2026.08.2",
            "prompt": "v14",
            "model": "springfield-model-v4",
            "policy": "springfield-policy-v3",
            "tools": "springfield-tools-v6",
        },
        cohort={"name": "springfield-canary", "window_minutes": 60},
        metrics=candidate,
        limits=limits,
        representative_trace_ids=["trace-sf-041", "trace-sf-087"],
        next_checks=[
            "Compare slow model and tool spans with v12",
            "Reproduce the highest-latency sanitized trace",
            "Add the confirmed failure to regression evaluation",
        ],
    )
    artifact_path = Path(__file__).with_name("springfield-canary-stop.json")
    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"Artifact: {artifact_path.name}")


if __name__ == "__main__":
    main()
