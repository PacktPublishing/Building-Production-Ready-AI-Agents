# Exercise 3: Swarm Pattern

## Premise

This exercise demonstrates parallel exploration with a Swarm pattern.

Multiple planners generate independent plans at the same time, and a merger selects a final plan.

Why this matters: Swarm is useful when you want diversity of candidate strategies before committing to one answer.

## Run Instructions

From this folder:

```bash
python solution.py
```

## Expected Output

You should see output headers/signals like:

- `[Swarm] Planning trip to Copenhagen...`
- `Running 3 planners in parallel...`
- `[Merger] Evaluating all plans...`
- `Swarm Result:` JSON block

Expected behavior:

- JSON includes:
  - `selected_plan`
  - `all_options`
- `all_options` contains multiple planner outputs.
- Final selection reflects merger scoring/ranking logic.
