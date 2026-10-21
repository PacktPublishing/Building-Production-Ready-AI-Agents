# Chapter 12 Code - Orchestration Patterns

This folder contains three small CLI apps that let you feel the difference between orchestration patterns instead of only reading about them.

Each example uses the same travel-booking scenario and the same Ollama-backed narrator. What changes is the orchestration strategy:

- `sequential.py`: one step completes before the next begins
- `parallel.py`: independent information gathering runs concurrently
- `routed.py`: the workflow branches based on policy outcome

## Why this matters

These examples are intentionally similar because the contrast is the lesson. When the domain stays stable, you can see exactly what orchestration changes in the control flow.

## Setup

1. Install dependencies:

```bash
uv sync
```

2. Make sure Ollama is running and a local model is available:

```bash
ollama pull qwen2.5:1.5b
```

The examples default to `qwen2.5:1.5b`, but you can override that with `OLLAMA_MODEL`.

## Run the examples

Sequential:

```bash
uv run sequential.py --request "Book a trip to Berlin next month with a budget of 900 dollars"
```

Parallel:

```bash
uv run parallel.py --request "Book a trip to Berlin next month with a budget of 900 dollars"
```

Routed:

```bash
uv run routed.py --request "Book a trip to Tokyo next month with a budget of 1800 dollars"
```

If the request is incomplete (for example only a budget), the CLI asks follow-up questions for missing destination, month, and traveler count before running orchestration.

In `routed.py`, if policy limits are not provided in the request or CLI flags, the demo asks for approval/block thresholds. If the policy route is `approval`, the demo asks for an explicit human approval decision before any booking execution happens.

## Optional environment variables

- `OLLAMA_HOST` (default: `http://127.0.0.1:11434`)
- `OLLAMA_MODEL` (default: `qwen2.5:1.5b`)

You can also override budget policy thresholds in any script:

```bash
uv run routed.py --request "Book a trip to Madrid with budget 1700" --approval-limit 1000 --blocked-limit 2500
```

For scripted runs, you can pass approval explicitly to avoid an interactive prompt:

```bash
uv run routed.py --request "Book a trip to Tokyo next month with budget 1800 for 1 traveler" --approval-limit 1000 --blocked-limit 2500 --approval-decision approve
```

## What to look for when you run them

- In `sequential.py`, notice how each stage waits for the previous one.
- In `parallel.py`, notice that the option gathering stage completes as one batch.
- In `routed.py`, notice that the same input can lead to different control paths depending on policy.

## Web workbench

If you want a visual way to compare strategy behavior, use the workbench app:

```bash
cd workbench
uv sync
uv run uvicorn app:app --reload --port 8012
```

Open `http://127.0.0.1:8012/` and compare:

- which questions are asked,
- when they are asked,
- and how routing changes by strategy and policy limits.