# Exercise 1 Solution: Inspect Priya's Run Context

This solution introduces the `Agent` class and passes trusted run context into its first method. Priya's task text remains untrusted input; it does not supply her identity.

## Follow the Boundary

The [starter](../exercises/exercise-1.py) leaves `Agent.run` unfinished. The completed method reads the trusted subject from `RunContext` instead of treating the task text as identity:

```python
class Agent:
    def run(self, task: str, context: RunContext) -> str:
        return f"{context.identity.subject}: {task}"
```

`RunContext` already carries a deadline and cancellation token, but this first stage does not enforce them. Exercise 5 introduces those checks at run entry and immediately before an external tool call.

## Open the Runnable Version

Open [exercise-1.py](./exercise-1.py) to see the method used with Priya's identity and the current deployment record.

## Prepare the Local Run

This exercise requires Python 3.11 or newer and [`uv`](https://docs.astral.sh/uv/). From the repository root, create the Chapter 18 environment:

```powershell
cd Chapter-18-Production/code
uv sync
```

This deterministic exercise does not require Ollama.

## Inspect the Context

```powershell
uv run python solutions/exercise-1.py
```

Expected output:

```text
Context stage: user-1842: Purchase FL-204
```

## What You Proved

The subject comes from application-controlled `RunContext`. This first `Agent` is deliberately small; each later exercise keeps it and adds the next production boundary.
