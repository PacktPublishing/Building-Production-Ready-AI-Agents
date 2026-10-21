# Exercise 5 Solution: Decide the Canary Action

This walkthrough shows how to run the canary decision tool and interpret the healthy and slow candidate results.

## Run the Tool

From `Chapter-19-Operating-and-Improving-Agents/code`, run:

```powershell
uv run python exercises/exercise-5.py
```

Expected output:

```text
Completion error-budget burn: 87.5%
Healthy canary action: advance
Slow canary action: rollback_and_investigate
Stopping reasons: ['p95_latency']
```

## Interpret the Output

### 1. Why may the healthy candidate advance?

The healthy candidate consumed 87.5% of the completion error budget, which is still below the 100% stopping limit. It also has enough runs, covers the full evaluation window, and keeps denials, latency, and cost within their limits.

The error budget is a limit, not a requirement to consume nothing. `Healthy canary action: advance` is therefore valid.

### 2. What stops the slow candidate?

`Stopping reasons: ['p95_latency']` identifies the only violated limit. The candidate's 95th-percentile latency is 8.6 seconds, above the eight-second objective.

The named reason preserves the evidence the team needs for the next investigation.

### 3. Why does completion not override latency?

Each rollout signal protects a separate part of the user experience. Acceptable completion does not cancel an unacceptable delay.

Because the slow candidate violates a defined objective, `rollback_and_investigate` returns its traffic to the stable release while the team follows the latency clue.
