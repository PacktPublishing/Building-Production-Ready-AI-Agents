# Chapter 14 Assignment: Multi-Agent Pattern Benchmark

## What This Assignment Covers

Chapter 14 taught you that pattern choice is not cosmetic architecture. It changes runtime behavior, cost profile, explainability, and failure modes. This assignment gives you a compact environment to prove that with data.

You will run two candidate patterns against the same travel request shape and compare latency, token estimate, and quality score before making a recommendation.

Why this matters: once teams move from one-agent demos to multi-agent systems, most production mistakes come from weak coordination design, not weak prompts.

## Premise of This Assignment

The assignment keeps one domain fixed while topology changes.

- Pattern A: Supervisor-Worker.
- Pattern B: Debate.
- Same request inputs.
- Same scoring dimensions.

That design gives you an apples-to-apples comparison you can defend.

## Why This Matters

If you benchmark only one pattern, you can tell if it works. You cannot tell if it was the right choice. This assignment teaches a repeatable evaluation loop:

1. Choose two plausible pattern candidates.
2. Run both under the same workload.
3. Compare outcomes with a fixed rubric.
4. Write a recommendation with clear switch conditions.

## File Map

- `main.py`: ASGI entrypoint for `uvicorn`.
- `webapp.py`: FastAPI routes for health, benchmark execution, and UI.
- `app_models.py`: request and response models for benchmark runs.
- `patterns.py`: two pattern simulators and winner-selection rule.
- `benchmark.py`: benchmark orchestration that returns the final report payload.
- `tests/test_assignment.py`: endpoint tests for health, benchmark contract, and UI route.
- `static/index.html`: tiny browser UI to run benchmark requests interactively.
- `solution/solution.py`: reference solution runner with recommendation output.

## Run the Assignment

```bash
cd Chapter-14-Multi-Agent-Patterns/assignment
uv sync
uv run uvicorn main:app --reload --port 8016
```

Open <http://127.0.0.1:8016> and click **Run Benchmark**.

Expected API path:

- `POST /api/benchmark` returns two pattern rows plus a winner and rationale.

## Test the Assignment

```bash
uv run --with pytest pytest tests/test_assignment.py -v
```

The tests confirm:

- API health route responds.
- Benchmark endpoint returns both patterns.
- Winner is one of the expected candidates.
- Root route serves the HTML scaffold.

## What To Try

Now move from single-run demo to useful comparison:

- Add at least 10 scenarios (easy, medium, hard).
- Keep scenario set identical for both patterns.
- Aggregate average latency and token estimate.
- Define one quality rubric and keep it stable across runs.
- Record a short recommendation memo with switch conditions.

## Suggested Study Questions

1. Which pattern gives the best quality-per-cost ratio in your scenario set?
2. Which pattern has the tighter latency distribution under load?
3. What scenario class flips your winner?
4. What fallback pattern would you adopt when constraints tighten?

## Next Step

After running benchmarks, compare your decisions with the reference implementation in `solution/solution.py`, then update your recommendation with explicit trigger conditions for switching patterns.
