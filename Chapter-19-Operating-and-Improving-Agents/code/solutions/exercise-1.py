from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitoring import should_alert, summarize_events


def build_events(
    agent_version: str,
    max_steps_runs: int,
    include_duplicate: bool = False,
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for run_number in range(100):
        run_id = f"{agent_version}-run-{run_number:03d}"
        events.append(
            {
                "event_type": "run_started",
                "run_id": run_id,
                "agent_version": agent_version,
            }
        )
        if run_number < max_steps_runs:
            terminal = {
                "event_type": "run_stopped",
                "run_id": run_id,
                "agent_version": agent_version,
                "reason": "max_steps",
            }
        else:
            terminal = {
                "event_type": "run_completed",
                "run_id": run_id,
                "agent_version": agent_version,
            }
        events.append(terminal)
        if include_duplicate and run_number == 0:
            events.append(dict(terminal))
    return events


def compare_versions(
    stable_events: list[dict[str, object]],
    candidate_events: list[dict[str, object]],
) -> tuple[dict[str, object], dict[str, object], bool]:
    stable = summarize_events(stable_events)
    candidate = summarize_events(candidate_events)
    pattern_detected = should_alert(
        current_rate=candidate["max_steps_rate"],
        baseline_rate=stable["max_steps_rate"],
        run_count=candidate["runs"],
        threshold=0.05,
        minimum_runs=100,
    )
    return stable, candidate, pattern_detected


def main() -> None:
    stable_events = build_events("travel-agent-stable", max_steps_runs=1)
    candidate_events = build_events(
        "travel-agent-2026.08.1",
        max_steps_runs=8,
        include_duplicate=True,
    )
    stable, candidate, pattern_detected = compare_versions(
        stable_events,
        candidate_events,
    )

    assert stable["runs"] == 100
    assert stable["max_steps_rate"] == 0.01
    assert candidate["runs"] == 100
    assert candidate["max_steps_rate"] == 0.08
    assert pattern_detected is True

    print(f"Stable: {stable['runs']} runs, max_steps={stable['max_steps_rate']:.1%}")
    print(
        f"Candidate: {candidate['runs']} runs, "
        f"max_steps={candidate['max_steps_rate']:.1%}"
    )
    print(f"Pattern detected: {pattern_detected}")


if __name__ == "__main__":
    main()