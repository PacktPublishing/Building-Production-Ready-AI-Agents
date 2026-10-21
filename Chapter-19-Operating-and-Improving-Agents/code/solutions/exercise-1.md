# Exercise 1 Solution: Compare the Candidate with the Baseline

This solution shows how to run the comparison tool and interpret its two operations: summarizing telemetry and evaluating the alert rule.

## Run the Tool

From `Chapter-19-Operating-and-Improving-Agents/code`, run:

```powershell
uv run python exercises/exercise-1.py
```

Expected output:

```text
Stable: 100 runs, max_steps=1.0%
Candidate: 100 runs, max_steps=8.0%
Candidate max_steps event deliveries: 9
Distinct affected candidate runs: 8
Candidate rate compared with baseline: 8x
Pattern detected: True
```

## Interpret the Output

### 1. Summarize the telemetry

The candidate reached `max_steps` in 8% of eligible runs, compared with 1% for the stable version. The candidate rate is therefore eight times the baseline.

The tool received nine candidate `max_steps` event deliveries but counted only eight affected runs. One event was delivered twice for the same `run_id`, so counting distinct runs prevents that duplicate from inflating the rate.

### 2. Evaluate the alert rule

`Pattern detected: True` means the candidate met all three alert conditions:

- Its 8% `max_steps` rate is above the 5% threshold.
- Its rate is at least twice the 1% baseline.
- The cohort contains the required 100 eligible runs.

This establishes that Priya's failure belongs to a wider production pattern. It does not identify which component caused the pattern. That is the next part of the investigation.
