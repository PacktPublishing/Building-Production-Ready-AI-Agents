"""Reference solution for Chapter 14 assignment scaffold.

Adds a simple recommendation helper and winner selection logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any


@dataclass
class RunMetrics:
    pattern: str
    latency_ms: float
    token_estimate: int
    quality_score: float
    recommendation: str


def recommend_winner(results: list[RunMetrics]) -> RunMetrics:
    """Score by quality first, then by lower token estimate as tie-break."""
    return sorted(
        results,
        key=lambda r: (r.quality_score, -r.token_estimate),
        reverse=True,
    )[0]


def run_supervisor_worker(request: dict[str, Any]) -> RunMetrics:
    start = perf_counter()

    destination = request.get("destination", "unknown")
    budget = request.get("budget", 0)
    recommendation = f"Supervisor-Worker: book best value option for {destination} under {budget}."

    elapsed_ms = (perf_counter() - start) * 1000.0
    return RunMetrics(
        pattern="supervisor-worker",
        latency_ms=elapsed_ms,
        token_estimate=1200,
        quality_score=0.74,
        recommendation=recommendation,
    )


def run_debate(request: dict[str, Any]) -> RunMetrics:
    start = perf_counter()

    destination = request.get("destination", "unknown")
    recommendation = (
        f"Debate: select judged tradeoff plan for {destination} balancing price and reliability."
    )

    elapsed_ms = (perf_counter() - start) * 1000.0
    return RunMetrics(
        pattern="debate",
        latency_ms=elapsed_ms,
        token_estimate=1700,
        quality_score=0.79,
        recommendation=recommendation,
    )


def run_assignment(request: dict[str, Any]) -> tuple[list[RunMetrics], RunMetrics]:
    results = [run_supervisor_worker(request), run_debate(request)]
    winner = recommend_winner(results)
    return results, winner


def print_report(results: list[RunMetrics], winner: RunMetrics) -> None:
    print("pattern,latency_ms,token_estimate,quality_score,recommendation")
    for row in results:
        print(
            f"{row.pattern},{row.latency_ms:.2f},{row.token_estimate},{row.quality_score:.2f},\"{row.recommendation}\""
        )
    print(f"\nRecommended pattern: {winner.pattern}")


if __name__ == "__main__":
    sample_request = {
        "destination": "Copenhagen",
        "dates": {"depart": "2026-08-12", "return": "2026-08-15"},
        "budget": 2200,
        "preferences": ["morning flight"],
        "approval_threshold": 1800,
    }
    rows, best = run_assignment(sample_request)
    print_report(rows, best)
