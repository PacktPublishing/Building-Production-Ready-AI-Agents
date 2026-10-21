from __future__ import annotations

from time import perf_counter

from app_models import BenchmarkResult, PatternRequest


def run_supervisor_worker(req: PatternRequest) -> BenchmarkResult:
    start = perf_counter()

    # Simulate decomposition + aggregation path.
    _ = f"search flights/hotels for {req.destination}"
    token_estimate = 1200
    quality_score = max(0.0, min(1.0, 0.74 + req.supervisor_quality_delta))

    elapsed = (perf_counter() - start) * 1000.0
    approved = req.budget <= req.approval_threshold
    return BenchmarkResult(
        pattern="supervisor-worker",
        latency_ms=elapsed,
        token_estimate=token_estimate,
        quality_score=quality_score,
        approved=approved,
    )


def run_debate(req: PatternRequest) -> BenchmarkResult:
    start = perf_counter()

    # Simulate cost-vs-reliability argument + judge pass.
    _ = f"debate travel options for {req.destination}"
    token_estimate = 1700
    quality_score = max(0.0, min(1.0, 0.79 + req.debate_quality_delta))

    elapsed = (perf_counter() - start) * 1000.0
    approved = req.budget <= (req.approval_threshold + 200)
    return BenchmarkResult(
        pattern="debate",
        latency_ms=elapsed,
        token_estimate=token_estimate,
        quality_score=quality_score,
        approved=approved,
    )


def pick_winner(results: list[BenchmarkResult], req: PatternRequest) -> BenchmarkResult:
    """Pick winner using configurable API knobs.

    Score =
      + quality_weight * quality_score
      - token_weight * normalized_token
      - latency_weight * normalized_latency
    """

    max_tokens = max(item.token_estimate for item in results) or 1
    max_latency = max(item.latency_ms for item in results) or 1.0

    def score(item: BenchmarkResult) -> tuple[float, float]:
        token_norm = item.token_estimate / max_tokens
        latency_norm = item.latency_ms / max_latency
        weighted = (
            (req.quality_weight * item.quality_score)
            - (req.token_weight * token_norm)
            - (req.latency_weight * latency_norm)
        )
        # Prefer lower token use on exact score ties.
        return weighted, -float(item.token_estimate)

    return sorted(results, key=score, reverse=True)[0]
