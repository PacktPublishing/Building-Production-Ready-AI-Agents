import runpy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any


SOLUTIONS = Path(__file__).with_name("solutions")
MONITORING = runpy.run_path(str(Path(__file__).with_name("monitoring.py")))


class MonitoringProjectionTests(unittest.TestCase):
    def test_conflicting_terminals_are_quarantined(self) -> None:
        events = [
            {"run_id": "eligible", "event_type": "run_completed"},
            {"run_id": "conflict", "event_type": "run_completed"},
            {"run_id": "conflict", "event_type": "run_stopped", "reason": "max_steps"},
            {"run_id": "incomplete", "event_type": "tool_completed"},
        ]

        summary = MONITORING["summarize_events"](events)

        self.assertEqual(summary["runs"], 1)
        self.assertEqual(summary["incomplete_runs"], 1)
        self.assertEqual(summary["quarantined_runs"], 1)
        self.assertEqual(summary["max_steps_rate"], 0.0)


class IncidentDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = runpy.run_path(str(SOLUTIONS / "exercise-2.py"))

    def test_isolated_prompt_regression_is_leading_hypothesis(self) -> None:
        rates = {"v12": 0.0, "v13": 1.0}
        versions = {
            "model": ("m1", "m1"),
            "prompt": ("v12", "v13"),
        }

        hypothesis, _ = self.module["identify_leading_hypothesis"](rates, versions)

        self.assertEqual(hypothesis, "prompt")

    def test_missing_or_ambiguous_evidence_is_undetermined(self) -> None:
        identify = self.module["identify_leading_hypothesis"]

        self.assertEqual(
            identify({}, {"prompt": ("v12", "v13")})[0],
            "undetermined",
        )
        self.assertEqual(
            identify(
                {"v12": 0.0, "v13": 1.0},
                {"prompt": ("v12", "v13"), "model": ("m1", "m2")},
            )[0],
            "undetermined",
        )

    def test_rates_exclude_incomplete_and_conflicting_runs(self) -> None:
        rates = self.module["failure_rates_by_prompt"](
            self.module["incident_events"]()
        )

        self.assertEqual(rates, {"v12": 0.0, "v13": 1.0})


class TelemetryReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        module = runpy.run_path(str(SOLUTIONS / "exercise-4.py"))
        cls.check_telemetry = staticmethod(module["check_telemetry"])
        cls.check_manifest = staticmethod(module["check_manifest"])
        cls.apply_budget = staticmethod(module["apply_budget"])
        cls.fingerprint_arguments = staticmethod(module["fingerprint_arguments"])

    def test_fingerprints_pass_but_nested_sensitive_data_fails(self) -> None:
        self.assertTrue(
            self.check_telemetry({"arguments_fingerprint": "hmac-sha256:example"})
        )
        self.assertFalse(
            self.check_telemetry({"details": [{"arguments": {"flight": "FL-204"}}]})
        )
        self.assertFalse(
            self.check_telemetry({"details": [{"authorization": "Bearer secret"}]})
        )

    def test_argument_fingerprints_are_scoped(self) -> None:
        arguments = {"destination": "Springfield"}
        first = self.fingerprint_arguments(arguments, b"key", "scope-a")
        repeated = self.fingerprint_arguments(arguments, b"key", "scope-a")
        other_scope = self.fingerprint_arguments(arguments, b"key", "scope-b")

        self.assertEqual(first, repeated)
        self.assertNotEqual(first, other_scope)

    def test_candidate_continues_but_over_budget_run_stops(self) -> None:
        self.assertEqual(self.apply_budget(model_steps=3, maximum_steps=4), "continue")
        self.assertEqual(self.apply_budget(model_steps=5, maximum_steps=4), "max_steps")

    def test_manifest_rejects_tampering_and_untrusted_issuer(self) -> None:
        deployment_path = Path(__file__).with_name("deployment.json")
        manifest = json.loads(deployment_path.read_text(encoding="utf-8"))

        for field, value in (
            ("artifact_digest", "sha256:" + "0" * 64),
            ("build_attestation", {**manifest["build_attestation"], "issuer": "other-ci"}),
        ):
            changed = {**manifest, field: value}
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", encoding="utf-8", delete=False
            ) as stream:
                json.dump(changed, stream)
                changed_path = Path(stream.name)
            try:
                self.assertFalse(self.check_manifest(changed_path)[1])
            finally:
                changed_path.unlink()


class CanaryDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module: dict[str, Any] = runpy.run_path(
            str(SOLUTIONS / "exercise-5.py")
        )

    def test_actions_cover_advance_hold_and_rollback(self) -> None:
        action = self.module["rollout_action"]

        self.assertEqual(action([]), "advance")
        self.assertEqual(action(["minimum_runs", "evaluation_window"]), "hold")
        self.assertEqual(action(["p95_latency"]), "rollback_and_investigate")

    def test_completion_error_budget_can_stop_rollout(self) -> None:
        signals = self.module["CanarySignals"]
        limits = self.module["RolloutLimits"]()
        control = signals(1000, 60, 0.94, 0.02, 6.4, 0.08)
        candidate = signals(200, 60, 0.90, 0.03, 7.2, 0.09)

        reasons = self.module["stopping_reasons"](control, candidate, limits)

        self.assertIn("completion_error_budget", reasons)


if __name__ == "__main__":
    unittest.main()
