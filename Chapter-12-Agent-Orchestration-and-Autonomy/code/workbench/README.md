# Orchestration Workbench

This mini web app lets you compare orchestration strategies by behavior, not just by code shape.

You can:

- drag workflow blocks from a palette into a decision canvas,
- switch strategy (`sequential`, `parallel`, `routed`) and see the canvas reshape,
- build flows in a strategy-native way:
  - sequential as a vertical chain,
  - parallel as intake -> fork -> horizontal branch set -> join,
  - routed as intake -> route decision -> branch columns,
- run a simulation and inspect:
  - what questions the user gets asked,
  - when those questions are asked,
  - which route is selected (`approved`, `approval`, `blocked`, etc).

Drop onto a node to insert after that node. Double-click a node to move it back to the palette.

## Why this matters

In real product teams, orchestration quality is often judged by interaction behavior:

- Does the user get asked too many questions too early?
- Are policy thresholds explicit or hidden?
- Does approval happen before execution?

This workbench makes those differences visible.

## Run

```bash
uv sync
uv run uvicorn app:app --reload --port 8012
```

Open:

- http://127.0.0.1:8012/

## Notes

- The app uses Ollama for run narration with fallback text if Ollama is unavailable.
- Default model: `qwen2.5:1.5b`.
- Optional env vars:
  - `OLLAMA_HOST` (default: `http://127.0.0.1:11434`)
  - `OLLAMA_MODEL` (default: `qwen2.5:1.5b`)
