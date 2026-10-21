# Exercise 2 Solution: Add an Approval Boundary

This solution extends the same Ollama agent with `purchase_flight`. The model still selects the tool and arguments, but the harness now decides whether the function may run.

It also carries forward the chapter's deadline boundary: Ollama uses a 30-second client timeout, and tool execution has a 5-second harness deadline. Approval does not replace bounded execution; both controls surround the same proposal.

## Continue the Agent

Run an unapproved purchase, a mismatched approval, and an exact approval through the Ollama tool loop, then prove whether the Python purchase function executed.

## The Approval Contract

Suppose the user approves `FL-999`, but Ollama proposes `purchase_flight(flight_id="FL-204")`. The tool name matches, yet the action does not. The boundary must compare the complete proposal before any purchase code runs.

That example gives this solution five concrete responsibilities:

- Register `search_flights` and `purchase_flight` with Ollama.
- Route Ollama's structured tool call through `execute_tool`.
- Bind approval to the exact tool name and arguments.
- Attach an idempotency key to the approved action.
- Track actual purchases separately from model output.

## Run the Three Paths

[exercise-2.py](./exercise-2.py) contains the cumulative agent with the approval boundary.

### Reuse the Exercise Environment

If you have not completed Exercise 1 setup, start Ollama and create the environment:

```powershell
ollama pull qwen2.5:1.5b
ollama serve
```

In a second terminal:

```powershell
cd Chapter-17-Agent-Harness/code/solutions
uv sync
```

### Deny Missing Approval

```powershell
uv run python exercise-2.py
```

The model requests the purchase tool, but the harness denies it before Python performs the side effect:

```text
Tool requested: purchase_flight({'flight_id': 'FL-204'})
Denied: Approval required for purchase_flight
Purchases: []
Termination reason: policy_denied
```

### Compare Mismatched and Exact Approval

First, prove that approval for another flight does not authorize `FL-204`:

```powershell
uv run python exercise-2.py --approved-flight FL-999
```

The model still requests `FL-204`, so the harness reports:

```text
Denied: Approval does not match the requested action
Purchases: []
Termination reason: policy_denied
```

Now approve the exact flight:

```powershell
uv run python exercise-2.py --approved-flight FL-204
```

This time the exact model-requested action passes the boundary:

```text
Tool requested: purchase_flight({'flight_id': 'FL-204'})
Purchases: ['FL-204']
Termination reason: completed
```

Model wording and argument formatting can vary. The `Purchases` list is the evidence that matters: it remains empty after denial and contains one flight after approval.

### Check Duplicate Suppression Without Ollama

Now test the idempotency behavior directly:

```powershell
uv run python exercise-2.py --check-replay
```

Expected output:

```text
First replayed: False
Second replayed: True
Purchases: ['FL-204']
```

The first call performs the side effect. The second carries the same action and idempotency key, so it returns the stored result without adding another purchase. This focused check consolidates duplicate suppression before Exercise 3 adds events.

## Follow the Boundary

`execute_tool` receives the real structured call returned by Ollama:

```python
name = call.function.name

if approval["tool"] != name or approval["arguments"] != arguments:
	raise PermissionError("Approval does not match the requested action")

key = approval["idempotency_key"]
if key in completed_actions:
	stored_fingerprint, stored_result = completed_actions[key]
	return stored_result, True
```

The policy surrounds tool execution. It does not depend on the model remembering a prompt instruction.

## What You Proved

The three runs establish a concrete policy boundary:

- Ollama can propose `purchase_flight` regardless of whether approval exists.
- Missing or mismatched approval stops execution before the purchase list changes.
- Exact approval changes application state once, while the idempotency key identifies a replay of that same action.
