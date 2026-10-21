# Exercise 3 Solution: Reject Tools Outside the Registry

This solution places an application-owned registry between a proposed tool call and Python execution. The model can name a tool, but only reviewed entries can reach a handler.

## Follow the Dispatch Path

The [starter](../exercises/exercise-3.py) leaves `Agent.execute_tool` unfinished. The solution performs three operations in order:

```python
spec = self.tools.get(name)
if spec is None:
    raise PermissionError("Tool is not registered")
self.authorize_tool(spec, arguments, context)
return spec.handler(arguments, context)
```

Lookup prevents invented names from selecting arbitrary code. The authorization method added in Exercise 2 then protects the registered handler.

## Open the Runnable Version

Open [exercise-3.py](./exercise-3.py) to see the registry and handler used by both calls.

## Prepare the Local Run

This exercise requires Python 3.11 or newer and [`uv`](https://docs.astral.sh/uv/). Prepare the shared environment:

```powershell
cd Chapter-18-Production/code
uv sync
```

This deterministic exercise does not require Ollama.

## Test Known and Unknown Tools

```powershell
uv run python solutions/exercise-3.py
```

Expected output:

```text
Isolation stage: Purchased FL-204 for user-1842
Unknown tool: Tool is not registered
```

## What You Proved

The known purchase reaches its reviewed handler after validation. The invented `delete_account` name stops at the registry and never selects an implementation.
