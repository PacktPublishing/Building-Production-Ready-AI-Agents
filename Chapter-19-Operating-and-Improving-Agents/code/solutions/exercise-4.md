# Exercise 4 Solution: Review the Candidate for Limited Exposure

This walkthrough shows how to run the readiness tool and decide whether the candidate may receive more traffic.

## Run the Tool

From `Chapter-19-Operating-and-Improving-Agents/code`, run:

```powershell
uv run python exercises/exercise-4.py
```

Expected output:

```text
Manifest verified: True
Telemetry safe: True
Unsafe telemetry rejected: True
Candidate budget decision: continue
Over-budget example decision: max_steps
Increase traffic: True
```

## Interpret the Output

### 1. What do the manifest and telemetry results establish?

`Manifest verified: True` means the candidate records valid full digests and that trusted fixture issuers signed the expected artifact and artifact-plus-dataset subjects. This binds the evaluation result to the candidate more strongly than field presence or a reused version label.

`Telemetry safe: True` shows that the approved example contains version and tool evidence without the sensitive fields rejected by the checker. `Unsafe telemetry rejected: True` confirms that the checker also rejects the supplied event containing raw tool arguments.

### 2. Why may the candidate enter the canary?

`Candidate budget decision: continue` shows that the corrected Springfield run used three model steps and remained within its four-step limit. Together with the manifest and telemetry checks, this permits a limited canary.

### 3. Why use a scoped HMAC fingerprint?

A plain hash of `Springfield` can be guessed by hashing a list of city names. An HMAC adds a protected key, and its bounded scope limits how long matching values can be linked. The local exercise key is a teaching fixture; production keys belong in a key-management system and never in telemetry.

### 4. What does the over-budget example establish?

`Over-budget example decision: max_steps` shows that the runtime still stops a different run that attempts a fifth model step. Passing the candidate review did not remove or weaken the safeguard.

`Increase traffic: True` therefore means the candidate may receive limited canary traffic. It does not authorize full rollout; the live canary signals still decide what happens next.
