# Exercise 2: Debate Pattern

## Premise

This exercise models explicit tradeoff reasoning using a Debate pattern.

Two agents argue competing priorities (cost versus comfort), and a judge selects the final option with rationale.

Why this matters: this pattern makes decision tradeoffs observable and auditable instead of hidden inside one agent response.

## Run Instructions

From this folder:

```bash
python solution.py
```

## Expected Output

You should see output headers/signals like:

- `[Debate] Evaluating flight options...`
- `[Cost Debater] ...`
- `[Comfort Debater] ...`
- `[Judge] Evaluating both arguments...`
- `Judge's Decision:` JSON block

Expected behavior:

- Final JSON includes:
  - `winner`
  - `selected_flight`
  - `reasoning`
- `selected_flight` includes flight details such as airline, price, and quality indicators.
