from __future__ import annotations

from pydantic import BaseModel, Field


class PatternRequest(BaseModel):
    destination: str = "Copenhagen"
    depart_date: str = "2026-08-12"
    return_date: str = "2026-08-15"
    budget: int = 2200
    approval_threshold: int = 1800
    preferences: list[str] = Field(default_factory=lambda: ["morning flight"])
    quality_weight: float = 1.0
    token_weight: float = 0.0
    latency_weight: float = 0.0
    supervisor_quality_delta: float = 0.0
    debate_quality_delta: float = 0.0


class BenchmarkResult(BaseModel):
    pattern: str
    latency_ms: float
    token_estimate: int
    quality_score: float
    approved: bool


class BenchmarkResponse(BaseModel):
    winner: str
    results: list[BenchmarkResult]
    rationale: str
