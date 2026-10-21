import math
import unittest

from app import (
    CanarySignals,
    CohortStats,
    RolloutLimits,
    build_investigation_artifact,
    build_springfield_fixture,
    completion_window_budget_consumption,
    leading_hypothesis,
    project_terminal_cohorts,
    rollout_action,
    stopping_reasons,
    validate_regression,
)


class CohortProjectionTests(unittest.TestCase):
    def test_fixture_has_required_counts_and_duplicate_is_invariant(self) -> None:
        fixture = build_springfield_fixture()
        with_duplicate = project_terminal_cohorts(fixture)
        without_duplicate = project_terminal_cohorts(fixture[:-1])

        self.assertEqual(with_duplicate, without_duplicate)
        self.assertEqual(
            with_duplicate["v12"],
            CohortStats(eligible=100, incomplete=2, quarantined=1, max_steps=1),
        )
        self.assertEqual(
            with_duplicate["v13"],
            CohortStats(eligible=100, incomplete=5, quarantined=1, max_steps=8),
        )
        self.assertEqual(with_duplicate["v12"].max_steps_rate, 0.01)
        self.assertEqual(with_duplicate["v13"].max_steps_rate, 0.08)

    def test_incomplete_runs_do_not_dilute_rate(self) -> None:
        events = [
            {"prompt_version": "v1", "run_id": "failed", "event_type": "run_stopped", "reason": "max_steps"},
            {"prompt_version": "v1", "run_id": "ok", "event_type": "run_completed"},
            {"prompt_version": "v1", "run_id": "partial", "event_type": "tool_completed"},
        ]

        cohort = project_terminal_cohorts(events)["v1"]

        self.assertEqual(cohort.eligible, 2)
        self.assertEqual(cohort.incomplete, 1)
        self.assertEqual(cohort.max_steps_rate, 0.5)

    def test_conflicting_terminals_are_quarantined(self) -> None:
        events = [
            {"prompt_version": "v1", "run_id": "conflict", "event_type": "run_completed"},
            {"prompt_version": "v1", "run_id": "conflict", "event_type": "run_stopped", "reason": "max_steps"},
        ]

        cohort = project_terminal_cohorts(events)["v1"]

        self.assertEqual(cohort, CohortStats(0, 0, 1, 0))

    def test_projection_is_independent_of_delivery_order(self) -> None:
        fixture = build_springfield_fixture()

        self.assertEqual(
            project_terminal_cohorts(fixture),
            project_terminal_cohorts(reversed(fixture)),
        )


class HypothesisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.old = CohortStats(100, 2, 0, 1)
        self.new = CohortStats(100, 5, 0, 8)

    def test_prompt_is_only_a_leading_hypothesis(self) -> None:
        self.assertEqual(
            leading_hypothesis(self.old, self.new, {"prompt"}), "prompt"
        )

    def test_ambiguity_returns_undetermined(self) -> None:
        cases = [
            (self.old, self.new, {"prompt", "model"}),
            (CohortStats(99, 0, 0, 1), self.new, {"prompt"}),
            (self.new, self.old, {"prompt"}),
        ]
        for old, new, changed in cases:
            with self.subTest(changed=changed, old=old, new=new):
                self.assertEqual(
                    leading_hypothesis(old, new, changed), "undetermined"
                )


class RegressionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario = {
            "expected_events": ["run_started", "tool_requested", "run_stopped"],
            "forbidden_events": ["unsafe_tool_executed"],
            "expected_termination": "max_steps",
        }
        self.trajectory = [
            "run_started",
            "model_requested",
            "tool_requested",
            {"event_type": "run_stopped", "reason": "max_steps"},
        ]

    def test_ordered_expected_events_allow_intervening_events(self) -> None:
        self.assertTrue(
            validate_regression(self.trajectory, self.scenario, "max_steps")
        )

    def test_wrong_order_fails(self) -> None:
        wrong_order = [
            "tool_requested",
            "run_started",
            {"event_type": "run_stopped", "reason": "max_steps"},
        ]
        self.assertFalse(validate_regression(wrong_order, self.scenario, "max_steps"))

    def test_forbidden_event_fails(self) -> None:
        trajectory = self.trajectory[:-1] + [
            "unsafe_tool_executed",
            self.trajectory[-1],
        ]
        self.assertFalse(validate_regression(trajectory, self.scenario, "max_steps"))

    def test_wrong_termination_fails(self) -> None:
        self.assertFalse(validate_regression(self.trajectory, self.scenario, "completed"))

    def test_multiple_terminal_events_fail(self) -> None:
        trajectory = self.trajectory + ["run_completed"]
        self.assertFalse(validate_regression(trajectory, self.scenario, "max_steps"))


class CanaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.control = CanarySignals(60, 100, 0.95, 0.01, 5.0, 0.08)
        self.healthy = CanarySignals(60, 100, 0.93, 0.02, 6.0, 0.09)
        self.limits = RolloutLimits()

    def test_completion_slo_one_has_defined_behavior(self) -> None:
        perfect_limits = RolloutLimits(completion_slo=1.0)
        perfect = CanarySignals(60, 100, 1.0, 0.0, 1.0, 0.01)
        imperfect = CanarySignals(60, 100, 0.99, 0.0, 1.0, 0.01)

        self.assertEqual(
            completion_window_budget_consumption(perfect, perfect_limits), 0.0
        )
        self.assertTrue(
            math.isinf(
                completion_window_budget_consumption(imperfect, perfect_limits)
            )
        )

    def test_advance_action(self) -> None:
        reasons = stopping_reasons(self.control, self.healthy, self.limits)
        self.assertEqual(reasons, [])
        self.assertEqual(rollout_action(reasons), "advance")

    def test_hold_action(self) -> None:
        short_window = CanarySignals(30, 50, 0.93, 0.02, 6.0, 0.09)
        reasons = stopping_reasons(self.control, short_window, self.limits)

        self.assertEqual(reasons, ["insufficient_window", "insufficient_traffic"])
        self.assertEqual(rollout_action(reasons), "hold")

    def test_rollback_action(self) -> None:
        slow = CanarySignals(60, 100, 0.93, 0.02, 9.0, 0.09)
        reasons = stopping_reasons(self.control, slow, self.limits)

        self.assertEqual(reasons, ["p95_latency"])
        self.assertEqual(rollout_action(reasons), "rollback_and_investigate")


class ArtifactTests(unittest.TestCase):
    def test_artifact_has_only_sanitized_structured_keys(self) -> None:
        metrics = CanarySignals(60, 100, 0.93, 0.02, 9.0, 0.09)
        limits = RolloutLimits()
        artifact = build_investigation_artifact(
            action="rollback_and_investigate",
            reasons=["p95_latency"],
            candidate_versions={"prompt": "v14", "model": "model-v4"},
            cohort={"name": "springfield-canary", "window_minutes": 60},
            metrics=metrics,
            limits=limits,
            representative_trace_ids=["trace-sf-041"],
            next_checks=["Compare sanitized latency spans"],
        )

        self.assertEqual(
            set(artifact),
            {
                "action",
                "reasons",
                "candidate_versions",
                "cohort",
                "metrics",
                "limits",
                "representative_trace_ids",
                "next_checks",
            },
        )
        serialized_keys = set()

        def collect_keys(value: object) -> None:
            if isinstance(value, dict):
                serialized_keys.update(value)
                for nested in value.values():
                    collect_keys(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect_keys(nested)

        collect_keys(artifact)
        self.assertTrue(
            {"prompt_text", "identity", "raw_arguments", "secret"}.isdisjoint(
                serialized_keys
            )
        )


if __name__ == "__main__":
    unittest.main()
