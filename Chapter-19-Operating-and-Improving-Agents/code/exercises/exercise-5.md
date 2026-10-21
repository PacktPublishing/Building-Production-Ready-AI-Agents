# Exercise 5: Advance, Hold, or Roll Back

The corrected candidate has reached the canary decision. In this exercise, you will operate a rollout tool that evaluates a healthy candidate and a candidate with the latency clue observed by the team.

The tool is already complete. Your task is to verify that the evidence leads to the correct operational action.

## Before You Start

Use Python 3.11 or newer. The tool uses only the standard library, so no dependency installation is required.

Run all commands from `Chapter-19-Operating-and-Improving-Agents/code`.

## Run the Tool

Run:

```powershell
uv run python exercises/exercise-5.py
```

## Interpret the Evidence

Before checking the reference output, predict the action for each candidate and name the signal that should stop rollout.

1. Why may the healthy candidate advance even after consuming 87.5% of its completion error budget?
2. Which signal stops the slow candidate?
3. Why does a healthy completion result not override the latency violation?

## Check Your Result

```text
Completion error-budget burn: 87.5%
Healthy canary action: advance
Slow canary action: rollback_and_investigate
Stopping reasons: ['p95_latency']
```

## Solution

Compare your interpretation with the [Exercise 5 walkthrough and answers](../solutions/exercise-5.md).
