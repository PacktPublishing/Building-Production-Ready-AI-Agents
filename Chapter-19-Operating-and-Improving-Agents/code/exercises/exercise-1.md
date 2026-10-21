# Exercise 1: Compare Priya's Candidate with the Baseline

Priya's trace shows one failed run. In this exercise, you will operate the monitoring tool to determine whether her experience belongs to a wider production pattern.

You will practice two operations:

1. **Summarize the telemetry:** Turn stable and candidate events into comparable `max_steps` rates.
2. **Evaluate the alert rule:** Decide whether the candidate rate is high enough, different enough from the baseline, and supported by enough runs to need attention.

## Before You Start

Use Python 3.11 or newer. The tool uses only the standard library, so no dependency installation is required.

Run all commands from `Chapter-19-Operating-and-Improving-Agents/code`.

## Run the Tool

The tool contains two controlled groups of 100 eligible runs:

1. The stable version completes 99 runs and reaches `max_steps` once.
2. Candidate `travel-agent-2026.08.1` completes 92 runs and reaches `max_steps` eight times.
3. One candidate `max_steps` event is delivered twice. The duplicate must not increase the affected-run count.

Run:

```powershell
uv run python exercises/exercise-1.py
```

## Interpret the Evidence

Before checking the reference output, write down the affected-run count, rate comparison, and whether you expect the alert rule to detect a pattern.

1. **Summarize:** Did the candidate reach `max_steps` more often than the stable version, and by how much? Why are nine event deliveries summarized as eight affected runs?
2. **Evaluate:** What does `Pattern detected: True` establish, and what does it not yet prove?

## Check Your Result

```text
Stable: 100 runs, max_steps=1.0%
Candidate: 100 runs, max_steps=8.0%
Candidate max_steps event deliveries: 9
Distinct affected candidate runs: 8
Candidate rate compared with baseline: 8x
Pattern detected: True
```

## Solution

Compare your interpretation with the [Exercise 1 walkthrough and answers](../solutions/exercise-1.md).
