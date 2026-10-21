# Exercise 3 Solution: Record the Denied Trajectory

This solution keeps the Ollama purchase flow from Exercise 2 and adds structured events around the model and tool boundaries.

The configured model and tool deadlines remain in place. Exercise 3 adds `model_failed`, `tool_failed`, and terminal events so those boundaries are observable as well as enforced.

## Continue from Approval

Run an unapproved purchase request and produce a trace that shows the model request, tool proposal, and policy denial in order.

## Evidence to Capture

For one denied purchase, the useful story is short: the model was called, it requested `purchase_flight`, policy denied that proposal, and the run stopped. The final answer may be empty, but these events still explain the result:

```text
model_requested -> tool_requested -> policy_denied -> run_stopped
```

To preserve that story, the solution makes the following additions:

- Preserve the live Ollama model and tool loop.
- Store events in the run state.
- Record model requests, tool requests, completed tools, denials, and termination.
- Print stable event fields without asserting against timestamps.

## Run the Observable Agent

[exercise-3.py](./exercise-3.py) contains the cumulative observable harness.

### Start the Existing Environment

Start Ollama if needed:

```powershell
ollama pull qwen2.5:1.5b
ollama serve
```

In a second terminal:

```powershell
cd Chapter-17-Agent-Harness/code/solutions
uv sync
```

### Inspect One Denied Run

```powershell
uv run python exercise-3.py
```

You should see the event sequence in this form:

```text
0 run_started
0 model_requested
1 tool_requested purchase_flight
1 policy_denied purchase_flight
1 run_stopped policy_denied
Purchases: []
Termination reason: policy_denied
```

The timestamp exists in each stored event but is omitted from this display because it changes on every run.

## Read the Event Story

The harness records the proposal before executing policy code:

```python
record_event(state, "tool_requested", tool=name, arguments=arguments)

try:
	result, replayed = execute_tool(
		call,
		self.tools,
		self.approval,
		self.completed_actions,
	)
except PermissionError as error:
	record_event(state, "policy_denied", tool=name, reason=str(error))
	state.termination_reason = "policy_denied"
	record_event(state, "run_stopped", reason="policy_denied")
	return state
```

If recording happened only inside `purchase_flight`, denied calls would be invisible because that function never executes.

## What You Proved

The event trace now answers questions the final answer cannot:

- `tool_requested` shows what the model proposed.
- `policy_denied` shows that application code rejected it.
- `run_stopped` and the empty purchase list prove where execution ended and that no side effect occurred.
