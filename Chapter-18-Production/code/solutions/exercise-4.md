# Exercise 4 Solution: Resume Priya's Interrupted Run

This solution keeps the earlier `Agent` methods, adds a durable store to the constructor, and makes `run` restore state through `load_or_create_run`.

## Restore State Without Exposing It

The [starter](../exercises/exercise-4.py) asks you to complete `Agent.load_or_create_run`. The solution treats the run ID as a lookup key, not a secret:

```python
state = self.store.load_checkpoint(run_id)
if state is not None:
    if state.subject != context.identity.subject or state.tenant != context.identity.tenant:
        raise PermissionError("Run belongs to another identity")
    return state
# Create and save a new RunState when no checkpoint exists.
```

A caller must match both the saved subject and tenant before receiving the checkpoint.

## Open the Runnable Version

Open [exercise-4.py](./exercise-4.py) to see the checkpoint written to a temporary SQLite database and restored under two identities.

## Prepare the Local Run

This exercise requires Python 3.11 or newer and [`uv`](https://docs.astral.sh/uv/). Prepare the shared environment:

```powershell
cd Chapter-18-Production/code
uv sync
```

This deterministic exercise does not require Ollama.

## Test Run Ownership

```powershell
uv run python solutions/exercise-4.py
```

Expected output:

```text
Checkpoint restored: run-priya-FL-204
Owner: user-1842
Different identity: Run belongs to another identity
```

## What You Proved

Priya can resume her saved conversation after a process interruption. Learning her run ID does not let another authenticated traveler read or continue that state.
