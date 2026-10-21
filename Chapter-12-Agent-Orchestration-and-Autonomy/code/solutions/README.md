# Chapter 12 Exercise Solutions

This folder contains runnable solution guides for the Chapter 12 exercises. The goal is to help readers build confidence by running known-good flows and checking observable outcomes.

Use this README as the entry point, then follow the per-exercise guides for exact commands.

## What is in this folder

- `exercise-1-patterns.md`: CLI solution run for sequential, parallel, and routed orchestration.
- `exercise-2-autonomy-gates.md`: CLI solution run for autonomy levels and approval gates using API calls.

## Prerequisites

- Python available on your machine.
- `uv` installed.
- For Exercise 1 narration: Ollama running locally with a model available.

## Install

Run these commands from the Chapter 12 `code/` folder:

```bash
cd Chapter-12-Agent-Orchestration-and-Autonomy/code
uv sync
```

For the autonomy app used in Exercise 2, run setup from its folder as well:

```bash
cd autonomy
uv sync
```

## Run the solutions

Start with the exercise-specific guides:

- Exercise 1: `solutions/exercise-1-patterns.md`
- Exercise 2: `solutions/exercise-2-autonomy-gates.md`

These guides are command-driven and designed to be reproducible.

## Expected output signals

Use these checks to confirm your run matches the intended behavior.

For Exercise 1:

- Sequential run shows stage-by-stage progression.
- Parallel run shows grouped independent work.
- Routed run changes path based on threshold policy (`approved`, `approval`, `blocked`).

For Exercise 2:

- Sessions move between `running`, `awaiting_manual`, and `completed`.
- Disabling manual checks reduces pause frequency.
- Keeping trade approval manual preserves human control for high-impact actions.

## Troubleshooting

If a command fails, use these quick checks first:

- Confirm you are in the correct folder before running `uv` commands.
- Ensure no other process is already using the selected port.
- For Exercise 2, confirm the API server is running before issuing `Invoke-RestMethod` commands.
