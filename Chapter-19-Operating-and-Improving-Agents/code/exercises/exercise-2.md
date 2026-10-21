# Exercise 2: Inspect the Deployment Difference

Production metrics show that Priya's failure belongs to a wider pattern. In this exercise, you will operate a deployment comparison tool to identify which component the evidence points to next.

The tool is already complete. Its fixture also includes one incomplete `v12` run and one `v13` run with conflicting terminal outcomes. Neither enters the rate denominator. Your task is to interpret the eligible-cohort output, not write code.

## Before You Start

Use Python 3.11 or newer. The tool uses only the standard library, so no dependency installation is required.

Run all commands from `Chapter-19-Operating-and-Improving-Agents/code`.

## Run the Tool

Run:

```powershell
uv run python exercises/exercise-2.py
```

## Interpret the Evidence

Before checking the reference output, predict which component the tool will identify and whether that result is a cause or a hypothesis.

1. Which component changed between the stable and candidate deployments?
2. Did the failure rate increase for the version containing that change?
3. Why must the incomplete and conflicting runs stay outside the denominator?
4. Does this evidence prove the prompt caused the failure, or does it make the prompt the leading suspect to reproduce next?

## Check Your Result

```text
Deployment manifest comparison:
  model: qwen2.5:1.5b -> qwen2.5:1.5b (unchanged)
  prompt: v12 -> v13 (changed)
  policy: v4 -> v4 (unchanged)
  tools: v7 -> v7 (unchanged)
Failure rates by prompt: {'v12': 0.0, 'v13': 1.0}
Leading hypothesis: prompt
Incident conclusion: The max_steps rate rose from 0% with v12 to 100% with v13; reproduce that isolated prompt change first.
```

## Solution

Compare your interpretation with the [Exercise 2 walkthrough and answers](../solutions/exercise-2.md).
