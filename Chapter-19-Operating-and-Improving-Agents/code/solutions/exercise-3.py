def build_regression_scenario() -> dict[str, object]:
    return {
        "name": "ambiguous destination requires clarification",
        "task": "Ask which state before searching for flights to Springfield",
        "expected_trajectory": [
            "run_started",
            "clarification_requested",
            "tool_requested:search_flights",
            "run_completed",
        ],
        "forbidden_events": ["max_steps"],
        "forbidden_before": {
            "tool_requested:search_flights": "clarification_requested",
        },
    }


def passes_regression(events: list[str], scenario: dict[str, object]) -> bool:
    expected = scenario["expected_trajectory"]
    forbidden = scenario["forbidden_events"]
    forbidden_before = scenario["forbidden_before"]
    expected_index = 0
    for event in events:
        if expected_index < len(expected) and event == expected[expected_index]:
            expected_index += 1

    forbidden_present = any(event in events for event in forbidden)
    too_early = any(
        event in events
        and (prerequisite not in events or events.index(event) < events.index(prerequisite))
        for event, prerequisite in forbidden_before.items()
    )
    return expected_index == len(expected) and not forbidden_present and not too_early


def main() -> None:
    scenario = build_regression_scenario()
    affected_events = ["run_started", "tool_requested:search_flights", "max_steps"]
    corrected_events = [
        "run_started",
        "clarification_requested",
        "tool_requested:search_flights",
        "run_completed",
    ]
    sensitive_fields = {"subject", "tenant", "prompt", "arguments"}

    affected_passes = passes_regression(affected_events, scenario)
    candidate_passes = passes_regression(corrected_events, scenario)
    sanitized = not sensitive_fields.intersection(scenario)

    assert affected_passes is False
    assert candidate_passes is True
    assert sanitized is True

    print(f"Affected agent passes: {affected_passes}")
    print(f"Candidate agent passes: {candidate_passes}")
    print(f"Scenario sanitized: {sanitized}")


if __name__ == "__main__":
    main()