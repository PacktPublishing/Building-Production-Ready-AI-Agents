import json
import unittest
from pathlib import Path


def passes_contract(events: list[str], scenario: dict[str, object]) -> bool:
    expected = scenario["expected_trajectory"]
    expected_index = 0
    for event in events:
        if expected_index < len(expected) and event == expected[expected_index]:
            expected_index += 1

    forbidden_present = any(event in events for event in scenario.get("forbidden_events", []))
    too_early = any(
        event in events
        and (prerequisite not in events or events.index(event) < events.index(prerequisite))
        for event, prerequisite in scenario.get("forbidden_before", {}).items()
    )
    return expected_index == len(expected) and not forbidden_present and not too_early


class RegressionScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        scenario_path = Path(__file__).with_name("regression-scenarios.json")
        cls.scenario = json.loads(scenario_path.read_text(encoding="utf-8"))[0]

    def test_corrected_trajectory_passes(self) -> None:
        events = [
            "run_started",
            "clarification_requested",
            "tool_requested:search_flights",
            "run_completed",
        ]
        self.assertTrue(passes_contract(events, self.scenario))

    def test_affected_trajectory_fails(self) -> None:
        events = ["run_started", "tool_requested:search_flights", "max_steps"]
        self.assertFalse(passes_contract(events, self.scenario))

    def test_out_of_order_trajectory_fails(self) -> None:
        events = [
            "run_started",
            "tool_requested:search_flights",
            "clarification_requested",
            "tool_requested:search_flights",
            "run_completed",
        ]
        self.assertFalse(passes_contract(events, self.scenario))


if __name__ == "__main__":
    unittest.main()