from __future__ import annotations

from app_models import BenchmarkResponse, PatternRequest
from patterns import pick_winner, run_debate, run_supervisor_worker


def run_benchmark(req: PatternRequest) -> BenchmarkResponse:
    results = [run_supervisor_worker(req), run_debate(req)]
    winner = pick_winner(results, req)

    rationale = (
        f"{winner.pattern} wins with weighted scoring "
        f"(quality_weight={req.quality_weight}, token_weight={req.token_weight}, "
        f"latency_weight={req.latency_weight})."
    )
    return BenchmarkResponse(winner=winner.pattern, results=results, rationale=rationale)
