# Exercise 1: Planner-Executor-Monitor with Ollama

This exercise implements three distinct classes that collaborate:

- **Planner**: Uses Ollama to generate or re-generate a structured plan.
- **Executor**: Executes plan steps against mocked travel services.
- **Monitor**: Detects failures, retries, escalates, and triggers replanning.

## Setup (uv)

1. Install dependencies:

```bash
uv sync
```

2. Ensure Ollama is running locally and a model is available:

```bash
ollama pull qwen2.5:1.5b
```

3. Run the demo:

```bash
uv run main.py
```

## Optional environment variables

- PLANNER_OLLAMA_HOST (default: http://localhost:11434)
- PLANNER_OLLAMA_MODEL (default: qwen2.5:1.5b)

Example:

```bash
PLANNER_OLLAMA_MODEL=qwen2.5:3b uv run main.py
```

## Extensions

The extensions folder contains focused, standalone variants of exercise1. Each one highlights a single capability so you can learn, run, and test it independently.

1. [01_add_new_step](extensions/01_add_new_step/README.md): Adds a new tool step (airport transfer) to the Planner-Executor-Monitor flow.
2. [02_config_driven_policies](extensions/02_config_driven_policies/README.md): Moves retry/approval behavior into JSON so policies can be tuned without code changes.
3. [03_hitl_specific_step](extensions/03_hitl_specific_step/README.md): Applies human-in-the-loop approval only for specific contexts (for example, longer trips).
4. [04_budget_constraints](extensions/04_budget_constraints/README.md): Adds a budget gate that validates estimated costs before execution continues.
5. [05_retry_strategies](extensions/05_retry_strategies/README.md): Demonstrates retry strategy variants (no retry, fixed, exponential backoff).

Extension index: [extensions/README.md](extensions/README.md)
