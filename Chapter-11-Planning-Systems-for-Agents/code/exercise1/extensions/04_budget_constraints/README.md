# 04 Budget Constraints

## Before -> After

Before: the agent could produce valid logistics but still exceed user budget.

After: monitor validates estimated total cost and triggers cheaper replanning when needed.

## User Benefit

Users get plans they can actually afford, not just plans that are technically executable.

## Where This Is Already Applied In This Extension

1. `main.py`: `_apply_extension_hooks(...)` collects budget and runs `estimate_trip_cost(...)` + `enforce_budget(...)`.
2. `main.py`: budget checks run before `monitor.oversee_execution(...)`, so over-budget plans are intercepted early.
3. `main.py`: on budget failure, the flow requests cheaper options before proceeding.

## Core Snippet

This snippet is the budget gate in the run pipeline: it validates estimated total cost and routes execution into budget-aware recovery when needed.

```python
ok, reason = enforce_budget(policy, estimated_total)
if not ok:
	# trigger replanning with cheaper options
```
## How To Run

1. cd Chapter-11-Planning-Systems-for-Agents/code/exercise1/extensions/04_budget_constraints
2. uv run main.py

## Test Run Instructions

1. cd Chapter-11-Planning-Systems-for-Agents/code/exercise1/extensions/04_budget_constraints
2. uv run --with pytest pytest -q test_extension.py
