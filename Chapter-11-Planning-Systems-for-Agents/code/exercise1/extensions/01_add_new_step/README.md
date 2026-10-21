# 01 Add New Step

## Before -> After

Before: the agent could only book flight, reserve hotel, and build itinerary.

After: the agent can also book airport transfer as part of the same plan flow.

## User Benefit

Before, users had to arrange transfer manually. Now the agent can complete the full end-to-end travel flow in one run.

## Where This Is Already Applied In This Extension

1. `main.py`: `_apply_extension_hooks(...)` calls `register_transfer_step(...)` during extension setup.
2. `executor.py`: `Executor.register_tool_handler(...)` registers `book_transfer` for runtime execution.
3. `main.py`: the transfer step is appended to the generated plan before monitor execution.

## Core Snippet

This snippet shows the exact wiring for this extension: register a new executable tool handler, then append the matching planning step so the monitor can execute it in the same run.

```python
executor.register_tool_handler(
		tool_name="book_transfer",
		handler=handle_transfer,
		policy=StepPolicy(max_retries=0),
)

plan.steps.append(
		PlanStep(description="Book airport transfer", tool="book_transfer", params=shared_params)
)
```
## How To Run

1. cd Chapter-11-Planning-Systems-for-Agents/code/exercise1/extensions/01_add_new_step
2. uv run main.py

## Test Run Instructions

1. cd Chapter-11-Planning-Systems-for-Agents/code/exercise1/extensions/01_add_new_step
2. uv run --with pytest pytest -q test_extension.py
