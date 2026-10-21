from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app_models import BenchmarkResponse, PatternRequest
from benchmark import run_benchmark

app = FastAPI(title="Chapter 14 Assignment API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/benchmark", response_model=BenchmarkResponse)
def benchmark(req: PatternRequest) -> BenchmarkResponse:
    return run_benchmark(req)


@app.get("/")
def index() -> FileResponse:
    path = Path(__file__).parent / "static" / "index.html"
    return FileResponse(path)
