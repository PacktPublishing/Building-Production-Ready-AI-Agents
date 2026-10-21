# Exercise 2 Solution: Inspect the Deployment Difference

This solution shows how to run the deployment comparison tool and decide which component the evidence points to next.

## Run the Tool

From `Chapter-19-Operating-and-Improving-Agents/code`, run:

```powershell
uv run python exercises/exercise-2.py
```

Expected output:

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

## Interpret the Output

### 1. Which component changed?

Only the prompt changed, from `v12` to `v13`. The model, policy, and tool versions remained the same.

### 2. Did the failure rate increase with that change?

Yes. The controlled events show a 0% `max_steps` rate for prompt `v12` and a 100% rate for prompt `v13`.

The denominator contains only runs with one unambiguous terminal outcome.

### 3. Why exclude incomplete and conflicting runs?

The incomplete run has no known outcome, so counting it would make `v12` look healthier without evidence. The conflicting run says both `completed` and `max_steps`; choosing either result would hide damaged evidence. The tool leaves the first incomplete and quarantines the second.

### 4. Is the prompt the proven cause?

No. The prompt is the **leading suspect** because it is the only changed component and the higher failure rate appears with its new version. This is evidence about where to investigate next, not proof of causation.

The team must now pin the model digest, model settings, tools, policy, runtime configuration, and retrieval data, then run the same sanitized scenario repeatedly with `v12` and `v13`. If the failure appears consistently with `v13`, does not appear with `v12`, and reverses when `v12` is restored, the prompt hypothesis becomes stronger. The team should still record the conditions and uncertainty rather than turn that result into an absolute causal claim.
