def incident_events() -> list[dict[str, str]]:
    return [
        {"run_id": "run-100", "agent_version": "current", "prompt_version": "v12", "event_type": "run_completed"},
        {"run_id": "run-101", "agent_version": "current", "prompt_version": "v12", "event_type": "run_completed"},
        {"run_id": "run-incomplete", "agent_version": "current", "prompt_version": "v12", "event_type": "tool_completed"},
        {"run_id": "run-102", "agent_version": "candidate", "prompt_version": "v13", "event_type": "tool_completed"},
        {"run_id": "run-102", "agent_version": "candidate", "prompt_version": "v13", "event_type": "run_stopped", "reason": "max_steps"},
        {"run_id": "run-103", "agent_version": "candidate", "prompt_version": "v13", "event_type": "tool_completed"},
        {"run_id": "run-103", "agent_version": "candidate", "prompt_version": "v13", "event_type": "run_stopped", "reason": "max_steps"},
        {"run_id": "run-conflict", "agent_version": "candidate", "prompt_version": "v13", "event_type": "run_completed"},
        {"run_id": "run-conflict", "agent_version": "candidate", "prompt_version": "v13", "event_type": "run_stopped", "reason": "max_steps"},
    ]


def failure_rates_by_prompt(events: list[dict[str, str]]) -> dict[str, float]:
    terminal_outcomes: dict[tuple[str, str], set[str]] = {}
    for event in events:
        if event["event_type"] == "run_completed":
            outcome = "completed"
        elif event["event_type"] == "run_stopped":
            outcome = event.get("reason", "stopped")
        else:
            continue
        key = (event["prompt_version"], event["run_id"])
        terminal_outcomes.setdefault(key, set()).add(outcome)

    eligible_outcomes: dict[str, list[str]] = {}
    for (version, _), outcomes in terminal_outcomes.items():
        if len(outcomes) == 1:
            eligible_outcomes.setdefault(version, []).append(next(iter(outcomes)))

    return {
        version: outcomes.count("max_steps") / len(outcomes)
        for version, outcomes in eligible_outcomes.items()
    }


def identify_leading_hypothesis(
    failure_rates: dict[str, float],
    component_versions: dict[str, tuple[str, str]],
) -> tuple[str, str]:
    changed_components = {
        component
        for component, (old_version, new_version) in component_versions.items()
        if old_version != new_version
    }
    if changed_components != {"prompt"}:
        return (
            "undetermined",
            "The deployment did not isolate one changed component.",
        )
    old_version, new_version = component_versions["prompt"]
    if old_version not in failure_rates or new_version not in failure_rates:
        return "undetermined", "Both prompt versions need observed runs."
    if failure_rates[new_version] <= failure_rates[old_version]:
        return "undetermined", "The new prompt has no higher failure rate."
    return (
        "prompt",
        f"The max_steps rate rose from {failure_rates[old_version]:.0%} with "
        f"{old_version} to {failure_rates[new_version]:.0%} with {new_version}; "
        "reproduce that isolated prompt change first.",
    )


def main() -> None:
    failure_rates = failure_rates_by_prompt(incident_events())
    component_versions = {
        "model": ("qwen2.5:1.5b", "qwen2.5:1.5b"),
        "prompt": ("v12", "v13"),
        "policy": ("v4", "v4"),
        "tools": ("v7", "v7"),
    }
    hypothesis, conclusion = identify_leading_hypothesis(
        failure_rates, component_versions
    )

    assert failure_rates == {"v12": 0.0, "v13": 1.0}
    assert hypothesis == "prompt"
    assert "v13" in conclusion

    print(f"Failure rates by prompt: {failure_rates}")
    print(f"Leading hypothesis: {hypothesis}")
    print(f"Incident conclusion: {conclusion}")


if __name__ == "__main__":
    main()