# Exercise 3: Move the Springfield Case from Red to Green

Prompt `v13` is the leading suspect. In this exercise, you will operate a regression tool that applies one sanitized behavior contract to the affected and corrected trajectories.

The tool is already complete. Your task is to verify what its results establish.

## Before You Start

Use Python 3.11 or newer. The tool uses only the standard library, so no dependency installation is required.

Run all commands from `Chapter-19-Operating-and-Improving-Agents/code`.

## Run the Tool

Run:

```powershell
uv run python exercises/exercise-3.py
```

## Interpret the Evidence

Before checking the reference output, predict which trajectory should satisfy the contract and what the sanitization check should report.

1. Why must the affected trajectory return `False` before the correction can be trusted?
2. What behavior allowed the candidate trajectory to return `True`?
3. What does `Scenario sanitized: True` establish about the regression fixture?

## Check Your Result

```text
Affected agent passes: False
Candidate agent passes: True
Scenario sanitized: True
```

## Solution

Compare your interpretation with the [Exercise 3 walkthrough and answers](../solutions/exercise-3.md).
