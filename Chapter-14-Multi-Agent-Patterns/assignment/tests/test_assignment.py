from __future__ import annotations

from pathlib import Path

from app_models import PatternRequest
from benchmark import run_benchmark
from webapp import health, index


def test_health() -> None:
    payload = health()
    assert payload["status"] == "ok"


def test_benchmark_returns_two_patterns() -> None:
    req = PatternRequest(
        destination="Copenhagen",
        depart_date="2026-08-12",
        return_date="2026-08-15",
        budget=2200,
        approval_threshold=1800,
        preferences=["morning flight"],
        quality_weight=1.0,
        token_weight=0.2,
        latency_weight=0.1,
        supervisor_quality_delta=0.0,
        debate_quality_delta=0.0,
    )
    payload = run_benchmark(req)

    assert len(payload.results) == 2
    assert payload.winner in {"supervisor-worker", "debate"}


def test_index_route_points_to_html() -> None:
    response = index()
    assert str(response.path).replace("\\", "/").endswith("static/index.html")
    assert Path(response.path).exists()
