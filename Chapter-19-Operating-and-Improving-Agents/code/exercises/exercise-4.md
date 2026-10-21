# Exercise 4: Clear the Candidate for Limited Exposure

The corrected candidate is almost ready for a canary. In this exercise, you will operate a readiness tool that checks digest-level provenance, rejects raw sensitive telemetry, creates a scoped HMAC fingerprint for comparison, and enforces the runtime step budget.

The tool is already complete. Your task is to decide whether the combined evidence permits more traffic.

## Before You Start

Use Python 3.11 or newer. The tool uses only the standard library, so no dependency installation is required.

Run all commands from `Chapter-19-Operating-and-Improving-Agents/code`.

## Run the Tool

Run:

```powershell
uv run python exercises/exercise-4.py
```

## Interpret the Evidence

Before checking the reference output, predict whether each gate will pass and whether the combined decision will permit limited traffic.

1. What do the manifest digests, attestations, and telemetry results allow the team to conclude?
2. Why may this candidate enter the canary?
3. Why is a scoped HMAC fingerprint safer than a plain hash for a destination such as Springfield?
4. What does the over-budget example prove would happen if a later run exceeded its limit?

## Check Your Result

```text
Manifest verified: True
Telemetry safe: True
Unsafe telemetry rejected: True
Candidate budget decision: continue
Over-budget example decision: max_steps
Increase traffic: True
```

## Solution

Compare your interpretation with the [Exercise 4 walkthrough and answers](../solutions/exercise-4.md).
