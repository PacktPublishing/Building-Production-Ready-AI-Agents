# Exercise 3 Solution: Verify the Springfield Regression

This walkthrough shows how to run the regression tool and interpret the affected and corrected trajectories.

## Run the Tool

From `Chapter-19-Operating-and-Improving-Agents/code`, run:

```powershell
uv run python exercises/exercise-3.py
```

Expected output:

```text
Affected agent passes: False
Candidate agent passes: True
Scenario sanitized: True
```

## Interpret the Output

### 1. Why must the affected trajectory fail?

The affected trajectory searches before requesting clarification and ends with `max_steps`. A regression that accepted this trajectory would not reproduce Priya's failure, so a later passing candidate would provide no evidence that the behavior was corrected.

`Affected agent passes: False` confirms that the contract detects the original problem.

### 2. Why does the candidate trajectory pass?

The candidate requests clarification before `search_flights`, then completes the run without `max_steps`. Its events satisfy the required order and avoid the forbidden outcome.

`Candidate agent passes: True` shows that the corrected behavior meets the same contract that rejected the affected version.

### 3. What does the sanitized result establish?

`Scenario sanitized: True` confirms that the fixture excludes the sensitive fields checked by this tool: identity, tenant, raw prompt, and raw tool arguments.

It does not prove that every possible sensitive value has been removed. Production sanitization still requires an approved schema and privacy review.
