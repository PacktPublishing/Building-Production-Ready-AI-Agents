# 03 HITL On Specific Step

## Before -> After

Before: approval behavior was static and did not depend on trip complexity.

After: `build_itinerary` asks for approval only when trip type is `1 week`.

## User Benefit

Users are interrupted less for simple trips, but still keep control when decisions have bigger impact.

## Where This Is Already Applied In This Extension

1. `main.py`: `_apply_extension_hooks(...)` calls `apply_contextual_hitl(executor)` for this extension.
2. `executor.py`: `build_itinerary` is re-registered with a conditional `StepPolicy` based on `trip_type`.
3. `monitor.py`: existing approval gates enforce this policy during execution.

## Core Snippet

This snippet shows the conditional policy branch that activates approval only for longer trips while keeping shorter flows fully automatic.

```python
if trip_type == "1 week":
	executor.register_tool_handler(
		"build_itinerary",
		handler,
		StepPolicy(requires_approval=True, approval_prompt="Approve 7-day itinerary generation?"),
	)
```
## How To Run

1. cd Chapter-11-Planning-Systems-for-Agents/code/exercise1/extensions/03_hitl_specific_step
2. uv run main.py

## Test Run Instructions

1. cd Chapter-11-Planning-Systems-for-Agents/code/exercise1/extensions/03_hitl_specific_step
2. uv run --with pytest pytest -q test_extension.py
