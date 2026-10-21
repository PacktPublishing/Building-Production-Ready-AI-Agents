# Exercise 1: Supervisor-Worker

## Premise

This exercise introduces the Supervisor-Worker pattern with a travel-booking scenario.

One supervisor receives a request, routes work to specialist workers, aggregates outputs, and returns a final recommendation with a policy check.

Why this matters: this is the baseline coordination topology for independent tasks. You should be able to see delegation, aggregation, and one clear decision point.

## Run Instructions

### Prerequisite For Tool-Calling Variant

The `tool_calling_solution.py` script uses Ollama directly for model-backed tool calls.

1. Install Ollama from [https://ollama.com/download](https://ollama.com/download)
1. Start Ollama (if not already running):

```bash
ollama serve
```

1. Pull a model (recommended default):

```bash
ollama pull llama3.1:latest
```

1. Optional sanity check:

```bash
ollama run llama3.1:latest "Say hello in one short sentence."
```

1. Install the Ollama Python SDK:

```bash
pip install ollama
```

If Ollama is not running or the model is missing, the tool-calling variant will fail fast with a clear error.

From this folder:

```bash
python solution.py
```

Optional tool-calling variant:

```bash
python tool_calling_solution.py
```

## Expected Output

### Baseline (`solution.py`)

You should see output headers/signals like:

- `[Supervisor] Received request: Copenhagen`
- `[Supervisor] Routing tasks to workers...`
- `[Flight Worker] Searching flights...`
- `[Hotel Worker] Searching hotels...`
- `[Policy Worker] Checking policy...`
- `Final Result:` JSON block

Expected behavior:

- A final recommendation is printed.
- `total_cost` is present.
- `policy_compliant` is present and boolean.

### Tool-calling Variant (`tool_calling_solution.py`)

You should see output headers/signals like:

- `[FlightWorker] Calling tool: find_flights`
- `[HotelWorker] Calling tool: find_hotels`
- `[PolicyWorker] Calling tool: check_policy`
- Final JSON object containing `request`, `recommendation`, `policy`, and `trace`.

Expected behavior:

- `trace` includes:
  - `request_received`
  - `flights_found`
  - `hotels_found`
  - `aggregation_complete`
  - `policy_checked`
