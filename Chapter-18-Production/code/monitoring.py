from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def load_events(path: str | Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict) or "event_type" not in value:
                raise ValueError(f"Invalid event at line {line_number}")
            events.append(value)
    return events


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid event timestamp: {value!r}") from error
    if parsed.tzinfo is None:
        raise ValueError("Event timestamps must include a timezone")
    return parsed


def filter_events(
    events: list[dict[str, Any]],
    tool: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict[str, Any]]:
    filtered = events
    if since is not None or until is not None:
        filtered = [
            event
            for event in filtered
            if "timestamp" in event
            and (since is None or parse_timestamp(event["timestamp"]) >= since)
            and (until is None or parse_timestamp(event["timestamp"]) < until)
        ]
    if tool is not None:
        scoped_run_ids = {
            event["run_id"]
            for event in filtered
            if event.get("tool") == tool and "run_id" in event
        }
        filtered = [
            event for event in filtered if event.get("run_id") in scoped_run_ids
        ]
    return filtered


def summarize_events(
    events: list[dict[str, Any]],
    tool: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    events = filter_events(events, tool=tool, since=since, until=until)
    observed_run_ids = {
        event["run_id"]
        for event in events
        if "run_id" in event
    }
    event_counts = Counter(event["event_type"] for event in events)
    denied_run_ids = {
        event["run_id"]
        for event in events
        if event.get("event_type") == "policy_denied" and "run_id" in event
        and (tool is None or event.get("tool") == tool)
    }
    terminal_events: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["event_type"] not in {
            "run_completed",
            "run_stopped",
            "run_paused",
        }:
            continue
        if "run_id" not in event:
            continue
        if tool is not None and event.get("tool") not in {None, tool}:
            continue
        terminal_events[event["run_id"]] = event
    termination_counts = Counter(
        event.get("reason", "completed") for event in terminal_events.values()
    )
    eligible_run_ids = set(terminal_events) | denied_run_ids
    incomplete_run_ids = observed_run_ids - eligible_run_ids
    run_count = len(eligible_run_ids)
    return {
        "runs": run_count,
        "incomplete_runs": len(incomplete_run_ids),
        "event_counts": dict(sorted(event_counts.items())),
        "termination_counts": dict(sorted(termination_counts.items())),
        "policy_denied_rate": (
            len(denied_run_ids) / run_count if run_count else 0.0
        ),
        "max_steps_rate": (
            termination_counts["max_steps"] / run_count if run_count else 0.0
        ),
        "tool_timeout_rate": (
            termination_counts["tool_timeout"] / run_count if run_count else 0.0
        ),
    }


def should_alert(
    current_rate: float,
    baseline_rate: float,
    run_count: int,
    threshold: float,
    minimum_runs: int,
    baseline_multiplier: float = 2.0,
) -> bool:
    if run_count < minimum_runs or current_rate <= threshold:
        return False
    if baseline_rate == 0:
        return current_rate > threshold
    return current_rate >= baseline_rate * baseline_multiplier


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize production agent events")
    parser.add_argument("events", nargs="?", default="events.jsonl")
    parser.add_argument("--policy-denied-threshold", type=float, default=0.05)
    parser.add_argument("--baseline-policy-denied-rate", type=float, default=0.01)
    parser.add_argument("--minimum-runs", type=int, default=100)
    parser.add_argument("--tool", help="Limit rates to runs involving this tool")
    parser.add_argument(
        "--window-minutes",
        type=float,
        help="Limit rates to events from the latest time window",
    )
    args = parser.parse_args()

    since = None
    if args.window_minutes is not None:
        since = datetime.now(timezone.utc) - timedelta(minutes=args.window_minutes)
    summary = summarize_events(load_events(args.events), tool=args.tool, since=since)
    summary["policy_denied_alert"] = should_alert(
        current_rate=summary["policy_denied_rate"],
        baseline_rate=args.baseline_policy_denied_rate,
        run_count=summary["runs"],
        threshold=args.policy_denied_threshold,
        minimum_runs=args.minimum_runs,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
