# 02 Config-Driven Policies

## Before -> After

Before: changing retries or approvals required editing Python code.

After: policy changes happen in `policy.json` without touching code.

## User Benefit

Agent behavior becomes predictable and easy to tune for different environments (dev/demo/prod) without redeploying logic.

## Where This Is Already Applied In This Extension

1. `main.py`: `_apply_extension_hooks(...)` calls `apply_policies_from_json(...)` and passes local `policy.json`.
2. `executor.py`: existing handlers are re-registered with updated `StepPolicy` values at runtime.
3. `policy.json`: retry/approval policy values are colocated with this extension and loaded at startup.

## Core Snippet

The first snippet is the integration call in extension setup; the second snippet is the policy application pattern that rewires each handler with JSON-driven behavior.

```python
apply_policies_from_json(
	executor,
	"extensions/02_config_driven_policies/policy.json",
)
```

```python
executor.register_tool_handler(
	tool_name=tool_name,
	handler=existing_handler,
	policy=StepPolicy(...),
)
```
## How To Run

1. cd Chapter-11-Planning-Systems-for-Agents/code/exercise1/extensions/02_config_driven_policies
2. uv run main.py

## Test Run Instructions

1. cd Chapter-11-Planning-Systems-for-Agents/code/exercise1/extensions/02_config_driven_policies
2. uv run --with pytest pytest -q test_extension.py
