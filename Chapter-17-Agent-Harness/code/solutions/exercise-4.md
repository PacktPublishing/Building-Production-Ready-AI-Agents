# Exercise 4 Solution: Test the Harness Without Ollama

The first three exercises used Ollama to produce real tool requests. This exercise removes the model from the test so we can prove that the runtime boundary works deterministically.

## Change the Testing Perspective

Test exact-action approval, idempotency, trajectory order, and step limits without starting an Ollama server.

## Guarantees Under Test

Start with one failure you never want a live model test to hide: approval names `FL-999`, the call requests `FL-204`, and the purchase list must remain empty. Constructing that call directly makes the policy result repeatable.

The full test file applies the same approach to six guarantees:

- Import the observable harness from Exercise 3.
- Construct structured tool calls directly.
- Prove that missing or mismatched approval cannot purchase a flight.
- Execute the same approved action twice and prove that one side effect occurs.
- Reject an event path containing an unexpected intermediate action.
- Reject reuse of one idempotency key for a different action.
- Replace `chat` with a fixed repeated tool request and prove the step limit stops it.

## Run Without Ollama

[exercise-4.py](./exercise-4.py) contains six pytest tests. It loads [exercise-3.py](./exercise-3.py), so the tests exercise the same policy and runtime code built in the previous exercise.

### Prepare pytest

From the repository root, install the shared exercise dependencies:

```powershell
cd Chapter-17-Agent-Harness/code/solutions
uv sync
```

Ollama does not need to be running for this exercise. The test controls the tool-call input and replaces the model call where necessary.

### Execute the Checks

```powershell
uv run pytest -q exercise-4.py
```

Expected output:

```text
......                                                                   [100%]
6 passed
```

## Prove Denial Before Side Effects

The mismatch test approves `FL-999` and requests `FL-204`:

```python
with pytest.raises(PermissionError, match="does not match"):
	execute_tool(
		tool_call("purchase_flight", flight_id="FL-204"),
		TOOLS,
		approval_for("FL-999"),
		completed_actions={},
	)
```

The assertion on the purchase list proves that denial happened before the side effect.

The trajectory test also exercises behavior rather than comparing two hard-coded lists. It records an unexpected search and the later denial into a real `RunState`, then passes that state to `trajectory_matches`. The evaluator returns `False` because the complete critical path contains the extra action.

## Prove Harness-Instance Duplicate Suppression

The idempotency test submits the same approved call twice with one in-memory `completed_actions` store. The first call executes the tool. The second returns the recorded result with `replayed=True`.

```python
assert first_replayed is False
assert second_replayed is True
assert purchases == ["FL-204"]
```

The next test reuses the key with `FL-999` and expects a conflict. This proves duplicate suppression inside one harness instance and keeps the key bound to its original action. A new instance has a new cache, so this does not claim exactly-once execution across instances, crashes, or workers; that requires shared durable storage and atomic updates.

## What You Proved

You can now distinguish two kinds of evidence:

- Live scenarios observe model-plus-runtime behavior.
- Direct tool-call tests prove approval and duplicate suppression without model variability.
- A constructed `RunState` proves trajectory evaluation, while a fixed model response proves the step limit.
