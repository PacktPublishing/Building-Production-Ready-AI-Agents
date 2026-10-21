# Assignment Solution: Standalone Travel Agent Evaluation

This solution builds a standalone travel-agent app and evaluates the app through Promptfoo's Python custom-provider interface. The agent uses frozen data, so the assignment measures tool routing and arguments rather than network availability.

## Problem

Build a standalone travel agent that calls both travel tools for a Seattle planning request, calls neither tool for an out-of-domain weather request, and exposes enough trace evidence for Promptfoo to verify both paths.

## What Is Required

- Implement `get_trips(destination)` and `get_hotels(destination)` with frozen data.
- Run a bounded Ollama tool loop and expose a Promptfoo-compatible `call_api` entry point.
- Trace `tool.name` and `tool.arguments` for each tool execution.
- Test the positive travel path and the negative out-of-domain path.
- Demonstrate that changing an expected destination to `Portland` causes the relevant trajectory assertion to fail.

## Solution Files

- [app.py](./app.py) contains the travel agent, tools, tracing, and `call_api` adapter.
- [promptfooconfig.yaml](./promptfooconfig.yaml) points Promptfoo at the app and defines the trajectory assertions.
- [pyproject.toml](./pyproject.toml) declares the app's Python dependencies.

These files form one runnable app. Promptfoo does not reproduce the agent logic in its configuration; it calls the app and evaluates the resulting output and trace.

## Step 1: Define the Tools

The app begins with two narrow tools:

```python
def get_trips(destination: str) -> dict[str, Any]:
	return {
		"destination": destination,
		"trips": [
			{"name": "Trip A", "transport": "train", "price_usd": 180},
			{"name": "Trip B", "transport": "flight", "price_usd": 260},
		],
		"source": "frozen assignment fixture",
	}


def get_hotels(destination: str) -> dict[str, Any]:
	return {
		"destination": destination,
		"hotels": [
			{"name": "Hotel A", "price_per_night_usd": 140},
			{"name": "Hotel B", "price_per_night_usd": 190},
		],
		"source": "frozen assignment fixture",
	}
```

Both tools accept the same simple argument. This keeps the assignment focused on whether the agent selected both sources, not on complex schemas.

## Step 2: Route Out-of-Domain Requests

Before exposing any tools, the app checks whether the prompt is about travel planning:

```python
def _is_travel_request(prompt: str) -> bool:
	travel_terms = ("trip", "travel", "hotel")
	return any(term in prompt.lower() for term in travel_terms)
```

If the request is outside that scope, the app returns a deterministic travel-only response before calling the model. A weather question therefore cannot invoke `get_trips` or `get_hotels`, even if the model would have misunderstood the instruction.

This application-level boundary is stronger than relying only on the system prompt. The Promptfoo test verifies the behavior with negative trajectory assertions.

## Step 3: Run a Bounded Tool Loop

The agent gives both functions to Ollama and records which tools run. It allows at most three tool rounds. If the model stops before calling both required tools, or exceeds that budget, the app returns an error instead of looping indefinitely.

Each tool execution creates a child span with three useful attributes:

```text
tool.name = get_trips
tool.arguments = {"destination": "Seattle"}
tool.result = { ... frozen trip data ... }
```

The same attributes are emitted for `get_hotels`. Promptfoo uses the first two as evidence for the trajectory assertions.

After both tools have run, the app makes one final model call without tools. That final call combines the frozen results into one recommendation.

## Step 4: Expose the Promptfoo Adapter

Promptfoo looks for `call_api` in `app.py`:

```python
def call_api(
	prompt: str, options: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
	model = options.get("config", {}).get("model", MODEL)
	# Run the agent inside the Promptfoo trace context.
	return {"output": _run_agent(prompt, model)}
```

The full solution also extracts Promptfoo's trace headers and creates the parent agent span. That connection places the tool spans inside the Trace Timeline for the test case.

## Step 5: Point Promptfoo at the App

The provider in `promptfooconfig.yaml` is `file://app.py`. Its configuration selects the model and the Python interpreter created by `uv sync`.

The configuration contains two tests. Together, they check both sides of the routing decision: when the app should use its travel tools and when it should keep them out of the workflow.

### Test 1: A Trip-Planning Prompt Calls Both Tools

The first test sends this request:

```text
Plan a trip to Seattle. Recommend one trip and one hotel.
```

This prompt contains a clear trip-planning request. The app should pass it to the agent with both tools available, and the agent should call `get_trips` and `get_hotels` with `Seattle` as the destination.

The test verifies:

| Metric | Evidence |
| --- | --- |
| `TripToolRouting` | `get_trips` appears in the trace. |
| `TripToolArguments` | `get_trips` received `destination: Seattle`. |
| `HotelToolRouting` | `get_hotels` appears in the trace. |
| `HotelToolArguments` | `get_hotels` received `destination: Seattle`. |
| `WorkflowHealth` | No trace span reported an error. |
| `FinalAnswer` | The answer contains `Seattle`, `trip`, and `hotel`. |

This test checks more than the final recommendation. The trajectory assertions prove that both required data sources contributed to the answer.

### Test 2: A Non-Trip Prompt Calls No Tools

The second test sends a weather request:

```text
What is the weather in Seattle?
```

This prompt mentions a city but does not ask for a trip or hotel. The app should recognize that it is outside the travel-planning scope, return its travel-only response, and call neither travel tool.

The test verifies:

| Metric | Evidence |
| --- | --- |
| `NoTripTool` | A weather request did not call `get_trips`. |
| `NoHotelTool` | A weather request did not call `get_hotels`. |
| `WorkflowHealth` | No trace span reported an error. |
| `OutOfDomainResponse` | The weather response states the app's travel scope. |

Notice that this test uses negative trajectory assertions. It passes only when `get_trips` and `get_hotels` are absent from the trace. This protects the app from treating every prompt that contains a destination as a travel request.

Taken together, the two tests define the routing boundary clearly. A trip prompt must use both tools, while a prompt without a trip-planning intent must use neither tool.

## Run the Solution

From the assignment directory:

```powershell
uv sync
ollama pull qwen3-vl:2b
ollama serve
```

In another terminal, run the configured evaluation with the Promptfoo command used in the chapter, then open its results viewer.

```powershell
npx promptfoo@0.121.19 eval -c promptfooconfig.yaml
npx promptfoo@0.121.19 view
```

Inspect the travel test's Trace Timeline and confirm that both tool spans are children of `agent travel workflow`. Then inspect the weather test and confirm that it contains no travel-tool spans.

The supplied provider configuration allows up to 15 minutes for each local call. If your hardware completes calls quickly, you can reduce `timeout`; if a slower but otherwise healthy run reaches the limit, increase it. The value is measured in milliseconds. Confirm that Ollama is running and the model is installed before extending the timeout, because configuration failures should be fixed rather than merely given more time.

## Test the Failure Case

Change the expected destination for `HotelToolArguments` from `Seattle` to `Portland`, then rerun the evaluation. The final answer may still look correct, but the argument assertion should fail because the trace records the actual call:

```text
get_hotels(destination="Seattle")
```

Restore `Seattle` after confirming the failure. This small mutation demonstrates the value of testing the execution path rather than trusting the final prose.

## Expected Outcome

The completed package proves two separate claims: a valid travel request uses both required data sources with the correct destination, and an out-of-domain request cannot invoke either travel tool. That evidence makes the assignment reviewable from both the final response and the execution trajectory.
