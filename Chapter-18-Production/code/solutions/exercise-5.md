# Exercise 5 Solution: Stop Before the Purchase Boundary

This solution checks cancellation and the remaining deadline immediately before an external tool could begin. Priya has already cancelled, so no purchase handler should start.

## Guard the Boundary

The [starter](../exercises/exercise-5.py) leaves the new `Agent.invoke_tool` method unfinished. `execute_tool` delegates to this boundary after registry and authorization checks:

```python
def invoke_tool(self, spec, arguments, context):
    context.cancellation.raise_if_cancelled()
    context.deadline.remaining_seconds()
    return spec.handler(arguments, context)
```

Cancellation is checked first because the application already knows the run should stop. If it remains active, the deadline then proves that time is still available.

## Open the Runnable Version

Open [exercise-5.py](./exercise-5.py) to see the token cancelled before the boundary is entered.

## Prepare the Local Run

This exercise requires Python 3.11 or newer and [`uv`](https://docs.astral.sh/uv/). Prepare the shared environment:

```powershell
cd Chapter-18-Production/code
uv sync
```

This deterministic exercise does not require Ollama.

## Observe the Stop

```powershell
uv run python solutions/exercise-5.py
```

Expected output:

```text
Purchase stopped: Run was cancelled
```

## What You Proved

Once the harness observes cancellation, it does not begin a new airline request. This does not undo a request that already reached the airline; that uncertain case needs reconciliation.
