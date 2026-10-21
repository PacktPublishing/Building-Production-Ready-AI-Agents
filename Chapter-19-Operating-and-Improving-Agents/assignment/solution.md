# Assignment Solution: Investigate and Stop the Springfield Canary

The Springfield incident contains three different kinds of evidence: terminal outcomes that can support a rate, unfinished runs that cannot yet support a rate, and contradictory runs that require investigation. This solution separates those cohorts before it attributes the change, preserves the failure as a regression, and decides whether the corrected canary should receive more traffic.

The completed [assignment implementation](./app.py) uses only the Python standard library and deterministic data. No model, network service, or production telemetry is required.

## Prepare the Local Run

Use Python 3.11 or newer. [`uv`](https://docs.astral.sh/uv/) is convenient but the project has no third-party dependencies.

```powershell
cd Chapter-19-Operating-and-Improving-Agents/assignment
uv sync
```

You can also use an existing Python 3.11+ interpreter directly:

```powershell
python -m unittest test_assignment.py
python app.py
```

## Canonicalize Terminal Outcomes

Begin with the event contract, not the rate calculation. A completed run and a stopped run use different event shapes, so project both into one controlled terminal vocabulary:

```python
def canonical_terminal(event):
    if event.get("event_type") == "run_completed":
        return "completed"
    if event.get("event_type") == "run_stopped":
        reason = event.get("reason")
        if not isinstance(reason, str) or not reason:
            raise ValueError("run_stopped requires a non-empty reason")
        return reason
    return None
```

`max_steps` is not a standalone event type in this contract. It is the reason on `run_stopped`. Other stop reasons remain visible instead of being folded into a generic failure.

## Project Trustworthy Cohorts

Next, group by both prompt version and run ID. Store terminal outcomes in a set so repeated delivery of the same outcome remains one outcome:

```python
outcomes_by_run = defaultdict(set)
seen_runs = set()

for event in events:
    key = (event["prompt_version"], event["run_id"])
    seen_runs.add(key)
    outcome = canonical_terminal(event)
    if outcome is not None:
        outcomes_by_run[key].add(outcome)
```

Classify each run only after all its events have been observed:

```python
if not outcomes:
    incomplete += 1
elif len(outcomes) > 1:
    quarantined += 1
else:
    eligible += 1
    if next(iter(outcomes)) == "max_steps":
        max_steps += 1
```

This order matters. Counting terminal event rows directly would inflate the numerator when delivery retries. Counting every seen run in the denominator would make incomplete runs falsely improve the rate. Choosing either outcome from a conflicting run would hide damaged evidence.

The fixture in [app.py](./app.py) creates exactly 100 eligible runs for each version, plus separate incomplete and conflicting runs. It also repeats one `v13` `max_steps` terminal. The resulting rates are therefore:

```text
v12: 1 / 100 = 1.0%
v13: 8 / 100 = 8.0%
```

## State a Leading Hypothesis

A rate increase identifies a changed pattern, not its cause. Return `prompt` only when the provenance and sample checks support that next investigation:

```python
def leading_hypothesis(old, new, changed_components, minimum_eligible=100):
    if (
        set(changed_components) == {"prompt"}
        and old.eligible >= minimum_eligible
        and new.eligible >= minimum_eligible
        and new.max_steps_rate > old.max_steps_rate
    ):
        return "prompt"
    return "undetermined"
```

This result means "investigate the isolated prompt change first." It does not prove that the prompt caused the Springfield loop. A model change, insufficient sample, or non-increasing rate makes the attribution ambiguous.

## Enforce the Regression Contract

Preserve the incident as a sanitized behavioral contract. The validator checks four independent requirements:

1. Expected events occur as an ordered subsequence, while unrelated diagnostic events may appear between them.
2. No forbidden event appears.
3. Exactly one terminal event appears.
4. The terminal event, the runtime's reported termination, and the scenario's expected termination all agree.

The ordered subsequence check advances one position only when the next expected event appears:

```python
expected_position = 0
for event_type in event_types:
    if (
        expected_position < len(expected_events)
        and event_type == expected_events[expected_position]
    ):
        expected_position += 1

if expected_position != len(expected_events):
    return False
```

After that structural check, derive the canonical termination from the single terminal event and compare all three values:

```python
return (
    event_termination == actual_termination
    and actual_termination == scenario["expected_termination"]
)
```

This final comparison prevents a trajectory ending in `run_completed` from passing a scenario that expects `max_steps`, even when its other expected events happen to match.

## Evaluate the Canary

`CanarySignals` and `RolloutLimits` reject negative counts, rates outside zero to one, and invalid limits before a rollout decision is made. The completion calculation describes consumption within this observation window:

```python
def completion_window_budget_consumption(signals, limits):
    allowed_incomplete_rate = 1.0 - limits.completion_slo
    observed_incomplete_rate = 1.0 - signals.completion_rate
    if allowed_incomplete_rate == 0.0:
        return 0.0 if observed_incomplete_rate == 0.0 else math.inf
    return observed_incomplete_rate / allowed_incomplete_rate
```

For the candidate, a 92% completion SLO permits 8% incomplete runs. The observed incomplete rate is 7%, so this window consumes `7% / 8% = 87.5%` of the allowed budget. This single-window ratio is not a multi-window error-budget burn rate.

A 100% SLO permits no incomplete runs. A perfect window therefore consumes zero; any incomplete run produces infinite consumption instead of division by zero.

Collect every stopping reason before choosing an action. The reference applies these rules:

```python
def rollout_action(reasons):
    if not reasons:
        return "advance"
    if set(reasons).issubset({"insufficient_window", "insufficient_traffic"}):
        return "hold"
    return "rollback_and_investigate"
```

The supplied canary has enough traffic and window coverage, and its completion, denial, and cost signals remain within their limits. Its nine-second p95 latency exceeds the eight-second limit, so the reason is `p95_latency` and the action is `rollback_and_investigate`.

## Preserve the Next Investigation

A stopped canary should leave an actionable, sanitized handoff. Build the artifact from controlled fields rather than copying a raw trace:

```python
artifact = {
    "action": action,
    "reasons": list(reasons),
    "candidate_versions": dict(candidate_versions),
    "cohort": dict(cohort),
    "metrics": asdict(metrics),
    "limits": asdict(limits),
    "representative_trace_ids": list(representative_trace_ids),
    "next_checks": list(next_checks),
}
```

The completed program writes this structure to `springfield-canary-stop.json`. It includes version identifiers and trace references needed to continue the investigation, but excludes prompt text, identity, raw tool arguments, and secrets.

## Run the Focused Tests

Run the standard-library suite:

```powershell
uv run python -m unittest test_assignment.py
```

Expected result:

```text
................
----------------------------------------------------------------------
Ran 16 tests

OK
```

The exact elapsed time may differ. The tests cover duplicate invariance, incomplete exclusion, conflicting terminal quarantine, delivery-order independence, attribution ambiguity, ordered and forbidden regression events, wrong termination, the 100% SLO edge case, all three rollout actions, and the artifact's approved keys.

## Run the Completed Investigation

```powershell
uv run python app.py
```

Expected output:

```text
v12: eligible=100 incomplete=2 quarantined=1 max_steps=1 rate=1.0%
v13: eligible=100 incomplete=5 quarantined=1 max_steps=8 rate=8.0%
Leading hypothesis: prompt
Affected scenario reproduced: True
Corrected regression passes: True
Wrong termination passes: False
Completion window budget consumption: 87.5%
Stopping reasons: p95_latency
Canary action: rollback_and_investigate
Artifact: springfield-canary-stop.json
```

Inspect `springfield-canary-stop.json` after the run. The assignment is complete when the tests pass, the output matches these deterministic decisions, and the generated artifact contains the next investigation without retaining sensitive source data.
