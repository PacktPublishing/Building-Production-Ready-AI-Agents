# Operating and Improving Agents in Production

Chapter 18 ended with Priya's `FL-204` booking safely recovered: one purchase completed, a second worker replayed the saved result, and durable events recorded both outcomes. That chapter established a resilient production runtime.

This chapter begins with the team's next production challenge. After noticing a behavior from the agent leading to fewer bookings, the team tried to improve the experience.

The team updated the system prompt to address that friction. The prompt became `travel-system-v13` and, with the unchanged model, policy, tools, and runtime, was packaged as candidate `travel-agent-2026.08.1`.

Before deployment, the team ran two kinds of checks. A **deterministic harness** repeated the same application-level checks for authorization, approval, duplicate-action prevention, and termination. An **offline evaluation** tried a prepared set of travel requests, including clear destinations, missing destinations, tool failures, and critical booking scenarios. The candidate passed both gates. Here, a **gate** is simply a check that must pass before the release may move forward.

Even so, the team released `travel-agent-2026.08.1` to only 5% of eligible users. Priya entered that group while planning another trip and asked for flights to Springfield without naming the state. The agent searched twice, reached `max_steps`, and returned no useful answer.

An attempt to remove friction had made the experience worse for some travelers.

The team now needs to determine whether its change explains the failure or whether another part of the system is involved.

Here are the stages the team is about to embark on to investigate the incident and improve the agent:

1. **Observe the change.** Logs and traces reconstruct Priya's run, while metrics determine whether similar failures increased across production traffic.
2. **Identify the likely cause.** Deployment records show what changed, and controlled reproduction tests whether the revised prompt explains the behavior.
3. **Correct the agent.** The team keeps the affected version stopped, updates the prompt so ambiguous destinations require clarification, and preserves the failure as a regression scenario.
4. **Return carefully to production.** A canary rollout compares the corrected candidate with the stable version and stops if quality, latency, cost, or safety signals exceed their limits.

> [!NOTE]
> `travel-agent-2026.08.1` through `travel-agent-2026.08.3`, and the `travel-system-v12` through `travel-system-v14` prompt versions, are controlled labels for this chapter's production scenario. The prompt changes and incident are supplied teaching fixtures, not hidden prompt files elsewhere in the repository.

## Learning Objectives

By the end of this chapter, you will be able to:

- Combine logs, metrics, and traces to understand agent behavior in production.
- Compare current behavior with a baseline and alert on sustained, meaningful changes.
- Investigate an incident and form an evidence-based hypothesis about the model, prompt, tool, policy, data, or runtime.
- Turn a sanitized production failure into a regression scenario and reevaluate a corrected candidate.
- Decide whether a candidate is ready for more traffic by checking provenance, privacy, runtime budgets, service objectives, and error-budget consumption.

## Before You Start

Chapter 18 explains how the production runtime creates and publishes the structured events used here. Priya's completed and replayed `FL-204` events demonstrated that this evidence survives a temporary destination failure. The exercises use controlled event data, Python 3.11 or newer, and only the standard library, so no model service or dependency setup is required. Each exercise provides its command when you reach it.

Each numbered exercise has a runnable `.py` file under `code/exercises` and a matching reference implementation under `code/solutions`. The files intentionally share most of their setup so you can focus on the small operational decision introduced at that stage; depending on the task, the exercise file either leaves that decision for you to implement or prints additional evidence for you to interpret. Run the exercise file first, follow its linked instructions, and use the solution file afterward to compare the relevant behavior rather than treating both directories as separate examples to complete.

## Clue One: Priya's Run Is Not Alone

As a first step in the investigation, the team stops further traffic to the candidate and returns that 5% slice to the stable version. That allows them to focus on diagnosing the issue.

The team starts with a simple question: was Priya's failed search an isolated case, or did the candidate fail more often than the stable version?

To answer it, the team examines Priya's trace to see exactly what happened during her request. It then checks production metrics to see how often the same failure occurred across other runs. The trace explains one failure; the metrics show whether it is part of a larger pattern.

### Reconstruct Priya's Failed Run

Priya saw only the failed result. The team needs to see what the agent actually did. It starts with the structured events recorded during her request.

Those events provide three useful views:

- A **log** records one fact. Example: `run_id=run-springfield-42 event=run_stopped reason=max_steps`.
- A **metric** summarizes many runs. For example, the candidate handled 100 completed or stopped requests, and 8 ended because the agent reached `max_steps`. Its `max_steps` rate is therefore 8%.
- A **trace** follows one request across the agent, model, and flight service. Example: `agent.run -> model.chat -> search_flights -> model.chat -> run.stop`.

Together, these views provide **observability**: enough evidence to understand the running system without reproducing every request.

A trace contains **spans**. A span records one timed operation, such as a model call or tool call. A **step**, by contrast, is one turn in the agent's control loop. One step can produce several spans because the agent may call both the model and a tool during that turn.

Priya's trace contains a span for the full run and a child span for each operation:

```text
agent.run run_id=run-springfield-42 duration=4.8s
├── model.chat step=1 duration=0.9s
├── tool.search_flights step=1 arguments_fingerprint=hmac-sha256:7ac9 duration=0.6s status=completed
├── model.chat step=2 duration=1.0s
├── tool.search_flights step=2 arguments_fingerprint=hmac-sha256:7ac9 duration=0.7s status=completed
├── model.chat step=3 duration=1.1s
└── run.stop step=3 reason=max_steps
```

The `step` field shows when an operation happened in the agent loop. The span shows what operation happened, how long it took, and whether it succeeded. Together, the spans form the trace of Priya's request.

The team can now interpret the trace:

- The matching scoped fingerprints show that the agent called `search_flights` twice with the same canonical input during this diagnostic window. Without a protected fingerprint or approved tool-argument data, the trace would show two calls but could not establish that their inputs matched.
- Both tool calls completed, so a flight-service error did not stop the run.
- The agent did not ask Priya which state she meant. If it had, the trace would show `clarification.requested step=1 field=destination status=waiting_for_user` before any search. Instead, the agent returned to the model and searched again.
- The third model call used the final allowed step, so the runtime stopped the run with `max_steps`.

At first, the limit may look too low. However, the agent repeated the same search without gaining new information. 

Giving it more steps could make the loop longer without producing a useful answer.

The more useful clue is the lack of progress: the agent should have asked which Springfield Priya meant before searching again. The trace explains how her request failed, but it does not yet show whether the prompt, model, or another component caused that behavior. It also does not show whether other travelers experienced the same problem.

Priya's trace explains her run. Next, the team must learn whether other runs failed the same way.

### Determine Whether the Failure Is a Pattern

Priya's trace gives the team one failed run. Now it needs something to compare that run with. Perhaps the travel agent has always reached `max_steps` occasionally, even before the new prompt entered production.

The team therefore compares the candidate with the stable version. The stable version provides the **baseline**: the agent's normal behavior before this deployment. The question becomes: did `max_steps` become more common after `travel-agent-2026.08.1` entered the canary?

Suppose the stable version reached `max_steps` once in 100 runs, while the candidate reached it eight times in 100 runs. Priya's failure would no longer look like an isolated event. It would be part of a larger change in behavior among users who received the candidate.

`max_steps` is the first signal the team follows because it matches Priya's failure. It also checks nearby signals in case the candidate changed the system in another way:

| Signal | What it may indicate |
| --- | --- |
| Increase in `policy_denied` | The model is proposing actions earlier or with different arguments |
| Increase in `max_steps` | The agent is looping, failing to use tool results, or receiving harder requests |
| Increase in `tool_timeout` | A dependency is slow, a deadline is too small, or a tool is overloaded |
| Duplicate-suppression rate | Clients or workers are retrying completed actions |
| Task completion decrease | Model, prompt, tool, retrieval, or policy behavior changed |
| Cost per successful run increase | More model turns or a more expensive route is being used |

The team separates these rates by agent version and request type so candidate behavior is not mixed with stable traffic. It does not use user IDs or raw prompts for this grouping because they may expose sensitive data and create too many distinct groups.

The [monitoring program](./code/monitoring.py) calculates denial, step-exhaustion, and tool-timeout rates. This logic stays outside `ProductionAgent`, where dashboards and alerts can use it.

Before trusting the comparison, the team must decide which runs count toward the rate. This group is called a **cohort**. For the Springfield investigation, three example runs look like this:

```text
run-1: flight search completed                  -> eligible
run-2: flight search stopped with max_steps     -> eligible
run-3: flight search started, no outcome yet    -> incomplete
```

An **observed run** has at least one matching event in the time window. An **eligible run** has a known outcome, so the team can classify it as completed or stopped. An **incomplete run** has no outcome yet. Only eligible runs enter the `max_steps` rate; incomplete runs are reported separately so they do not make the candidate look healthier than it is.

With a stable baseline and a clearly defined cohort, the team can now ask whether Priya's failure represents a real production change rather than normal variation.

### Detect When the Pattern Needs Attention

Comparing the two rates will show whether the candidate behaves differently. The team also needs a rule that decides when the difference is large enough to require attention. That rule produces an **alert signal**.

The [monitoring program](./code/monitoring.py) provides the two operations the reader will use in Exercise 1:

1. `summarize_events` turns the stable and candidate events into measurements such as the `max_steps` rate.
2. `should_alert` compares the candidate rate with the baseline and the team's limits.

The two operations connect like this:

```python
stable = summarize_events(stable_events)
candidate = summarize_events(candidate_events)

alert = should_alert(
	current_rate=candidate["max_steps_rate"],
	baseline_rate=stable["max_steps_rate"],
	run_count=candidate["runs"],
	threshold=0.05,
	minimum_runs=100,
)
```

The detector returns `True` only when there is enough evidence and the candidate rate is both above 5% and at least twice the baseline. The same function can watch another rate, such as `tool_timeout_rate` or `policy_denied_rate`, by supplying that measurement and its appropriate limits.

```text
production events
	-> summarize_events
	-> rate
	-> should_alert
	-> alert signal
```

The alert signal and its delivery are separate. This chapter's code calculates `True` or `False`. In production, a monitoring platform would evaluate the rule repeatedly over a rolling window and turn `True` into an on-call page or incident message.

An alert is also different from a test. A test sends a known scenario through the agent and checks its expected behavior, usually before deployment. An alert evaluates measurements from real production runs after deployment. It can show that behavior changed enough to investigate, but it does not explain the cause.

### Exercise 1: Compare Priya's Candidate with the Baseline

Now take the team's place in the investigation. Operate the monitoring tool to summarize the stable and candidate telemetry, apply the alert rule, and decide what the result establishes.

[Open Exercise 1: Compare Priya's Candidate with the Baseline](./code/exercises/exercise-1.md)

The team now has automatic evidence that the candidate changed production behavior. The next question is what changed inside the candidate.

## Clue Two: Only the Prompt Changed

The metrics answer the first question: Priya's run was not isolated. The candidate reaches `max_steps` more often than the stable version.

Now the team asks: what changed? It compares the two deployment records. The model, policy, tools, and runtime are the same. Only the prompt changed, from `travel-system-v12` to `travel-system-v13`.

This comparison does not require someone to remember every deployment detail or write incident-specific code. In production, the deployment system should keep an immutable manifest for each release. A deployment dashboard, CI artifact comparison, or manifest-diff command can then show which component versions changed. This chapter provides that comparison as a ready-to-run tool in Exercise 2.

This makes the prompt the leading suspect, but it is not proof. The team must compare the old and new prompts under the same pinned conditions before deciding how much confidence that explanation deserves.

An agent has many moving parts. The problem could come from the model, prompt, data, tool, policy, or runtime. Changing the wrong part may hide the symptom without fixing the cause.

Suppose an alert shows that the new agent version repeatedly reaches `max_steps` after `search_flights`. The team can follow this process:

1. **Contain:** Pause the deployment, route traffic to the previous version, disable the affected tool, or reduce autonomy according to severity.
2. **Preserve evidence:** Save redacted traces, stable events, version metadata, and external transaction identifiers.
3. **Classify the failure:** Decide whether it belongs to the model, prompt, context, tool, policy, runtime, or dependency.
4. **Reproduce:** Build the smallest deterministic test or live scenario that demonstrates the behavior.
5. **Fix:** Change the responsible component without weakening unrelated safety boundaries.
6. **Evaluate:** Run deterministic harness tests and the expanded scenario suite.
7. **Deploy gradually:** Use a canary or staged rollout and compare production signals with the previous version.
8. **Close the loop:** Document the cause, response, and new regression coverage.

These containment actions should be ready before an incident. The team should be able to disable a tool, switch to read-only mode, reduce step limits, or return to a stable version without making emergency code or prompt edits.

### Exercise 2: Inspect the Deployment Difference

The alert shows when the failure increased. Now operate the deployment comparison tool and decide whether its evidence identifies a proven cause, a leading suspect, or an undetermined result.

[Open Exercise 2: Inspect the Deployment Difference](./code/exercises/exercise-2.md)

## Reproduce the Failure Before Fixing It

Here is what the team knows so far: Priya's trace shows the agent repeating the same search without asking for clarification, production metrics show that `max_steps` increased with the candidate, and the deployment comparison identifies prompt `v13` as the only changed component. The prompt is now the leading suspect, so the investigation pivots from detecting the problem to reproducing it under controlled conditions.

A reproduction test checks whether the observed behavior follows the suspected change under controlled conditions. The affected prompt must fail the Springfield test before the team changes it. Otherwise, a later passing test would not show that the correction addresses the behavior seen in production.

The team creates a simple rule: when a traveler says Springfield without naming the state, the agent must ask which state before searching. The test keeps this behavior but removes Priya's identity and exact words.

### Build a Reproduction Without Copying Priya

The test must compare `travel-system-v13` with its control without copying Priya's data. Her trace provides the behavior, but her account and raw conversation do not belong in source control. The team turns the case into a generic Springfield scenario.

Without a regression test, the same failure could return after a later model, prompt, or tool change.

The test stores the required behavior, not the raw request:

```json
{
	"name": "ambiguous destination completes after clarification",
	"task": "Find a flight to Springfield; ask which state before searching",
	"expected_trajectory": [
		"run_started",
		"clarification_requested",
		"tool_requested:search_flights",
		"run_completed"
	],
	"forbidden_events": [
		"max_steps"
	],
	"forbidden_before": {
		"tool_requested:search_flights": "clarification_requested"
	},
	"expected_termination": "completed"
}
```

The scenario requires clarification before `search_flights`, followed by a completed run. A candidate cannot pass by asking a question and stopping, or by searching too early. If exact wording matters, keep it in an approved restricted dataset rather than source control.

The [regression scenario](./code/regression-scenarios.json) is separate from production telemetry. The test checks affected, corrected, and out-of-order runs. This keeps raw operational data out of the repository while making the approved scenario executable.

Run that contract test directly:

```powershell
uv run python -m unittest test_regression.py
```

The local test uses fixed event sequences, so it verifies the regression contract deterministically. It does not execute a model and cannot establish that prompt `v13` caused the production change by itself.

For the live reproduction, the team pins the model digest, model settings, tools, policy, runtime configuration, and retrieval data. It then runs the same sanitized scenario repeatedly with prompt `v12` and prompt `v13`. The result supports the prompt hypothesis only if the failure appears consistently with `v13`, does not appear with `v12`, and reverses when the control prompt is restored. Repetition matters because model inference and hosted dependencies may still vary even when the team pins every available setting.

The complete feedback loop is now visible:

```text
production signal
	-> representative trace
	-> leading hypothesis and reproduction
	-> sanitized regression scenario
	-> deterministic tests and live evaluation
	-> staged deployment
	-> production comparison
```

Runtime tests come first. Live model evaluation begins only after authorization, idempotency, cancellation, and other application controls pass.

### Change the Prompt, Then Reevaluate

First, the team runs the repeated, pinned comparison. The `v13` runs reproduce Priya's pattern by searching before asking which Springfield she means, while the `v12` control runs do not. This strengthens the prompt hypothesis enough to justify a targeted correction, but the team still records the experimental conditions and avoids claiming certainty beyond the evidence.

Now the team updates the prompt. `travel-system-v14` still avoids unnecessary questions, but it asks for clarification when a destination is ambiguous. With all other components unchanged, it becomes candidate `travel-agent-2026.08.2`.

Fix the component supported by the evidence. A prompt or orchestration problem belongs there. A tool validation problem belongs in the tool schema or validation. Do not weaken unrelated safety controls.

Run the Springfield test and the full deterministic suite again. If both pass, the corrected version may enter another canary. It is not yet ready for all traffic.

### Exercise 3: Move the Springfield Case from Red to Green

The investigation has reached its first decisive experiment. Operate the regression tool and verify that one sanitized contract rejects the affected behavior and accepts the correction.

[Open Exercise 3: Move the Springfield Case from Red to Green](./code/exercises/exercise-3.md)

The exercise uses controlled event trajectories rather than a live model so the regression result stays deterministic. A live evaluation can follow after the runtime suite and scenario contract pass.

## The Corrected Agent Returns Under Observation

The Springfield regression now passes with prompt `v14`. That is encouraging, but it proves only that the corrected candidate handles one known scenario. The team still needs to see how `travel-agent-2026.08.2` behaves with real traffic.

Before that can happen, the investigation asks three practical questions:

1. Are we testing the exact build that passed the regression?
2. Can we inspect its behavior without keeping Priya's sensitive data?
3. Will the runtime stop work that exceeds its time or cost limits?

Only after all three answers are supported by evidence will the team start another small canary.

### Are We Testing the Exact Corrected Build?

The team first checks the candidate's identity. Prompt `v14` is supposed to be the only behavioral correction. If an unrecorded model, policy, or tool change entered the same package, a good or bad canary result would be difficult to explain.

The evidence for this question is the deployment manifest. It records the **provenance** of the candidate: the components, immutable digests, configuration, and attestations that produced its behavior.

Record an immutable manifest for each deployment:

```json
{
	"agent_version": "travel-agent-2026.08.2",
	"artifact_digest": "sha256:55a8d26f4e03f9b7...",
	"build_attestation": {
		"issuer": "chapter-ci",
		"subject": "sha256:55a8d26f4e03f9b7...",
		"signature": "hmac-sha256:..."
	},
	"dependency_lock_digest": "sha256:b6640f8b6b78318a...",
	"source_revision": "8f23c1d",
	"model": "qwen2.5:1.5b",
	"model_digest": "sha256:c1b7f4a984cbf22d...",
	"prompt_version": "travel-system-v14",
	"prompt_digest": "sha256:987b38db5c18770f...",
	"policy_version": "purchase-policy-v4",
	"runtime_config_digest": "sha256:089c7acb41d7575d...",
	"tool_schema_version": "travel-tools-v7",
	"evaluation_dataset": "travel-critical-v9",
	"evaluation_dataset_digest": "sha256:9c208af4e68437db...",
	"evaluation_attestation": {
		"issuer": "chapter-evaluator",
		"subject": "artifact-digest:dataset-digest",
		"signature": "hmac-sha256:..."
	},
	"deployment_time": "2026-08-02T09:00:00Z"
}
```

The digests are abbreviated here for readability; production records keep the full cryptographic values. A signed build attestation binds the artifact digest to a trusted build identity. The evaluation attestation binds that artifact digest to the digest of the dataset it passed. The local standard-library exercise simulates trusted issuers with HMAC signatures; a production system should verify signatures or KMS-backed attestations against managed trust roots and protected keys. The record is **immutable**: after deployment, the team creates a new manifest instead of editing this one. Its identifier travels with traces and evaluation reports.

The local [deployment manifest](./code/deployment.json) demonstrates this record. In a production system, a deployment dashboard, CI artifact, or manifest-diff tool should provide the same comparison without requiring incident-specific code.

The first answer is now clear: the canary will test the same component combination that passed the Springfield regression.

### Can We Investigate Without Keeping Priya's Data?

The manifest answers which build produced a run. The team must next decide what evidence that run may retain.

Priya's original trace may contain an account ID, her exact request, and raw `search_flights` arguments. The team needed the repeated-search pattern, but it did not need those identifying details in routine telemetry or source control. Keeping everything would turn observability into a second, poorly controlled copy of traveler data.

The team therefore classifies each field before telemetry leaves the process:

Classify each field in the event contract:

| Data class | Example | Default handling |
| --- | --- | --- |
| Operational | termination reason, duration | Retain in metrics using bounded labels |
| Identifying | user ID, tenant ID | Tokenize or use a scoped keyed fingerprint when direct identity is unnecessary |
| Sensitive content | prompt, tool arguments | Redact or omit; restrict diagnostic sampling |
| Secret | API key, access token | Never send to the model, logs, traces, or metrics |
| Audit | approval ID, policy decision | Store immutably with access controls and defined retention |

For Priya's tool calls, routine telemetry keeps the tool name and a scoped keyed fingerprint rather than the original destination:

```json
{
	"tool": {
		"name": "search_flights",
		"arguments_fingerprint": "hmac-sha256:example"
	}
}
```

A plain hash is not enough for a low-entropy value such as a city name: an attacker could hash a list of likely cities and compare the results. Instead, the telemetry service canonicalizes the approved fields and computes an HMAC with a protected key. Matching fingerprints within the same scope let the team compare calls without recording the input.

The HMAC key stays in a key-management system, not in the event. The team rotates the key or includes a bounded scope, such as an incident and date, so the same traveler cannot be linked indefinitely across datasets. This still leaves limited linkability inside that scope, which the privacy review must document. **Redaction** removes content, while **tokenization** replaces it with a controlled value that an authorized system may resolve later.

When an incident truly needs richer evidence, the team can use approved **diagnostic sampling** for a small number of runs. Those traces still need redaction, restricted access, and a short retention period. Aggregate metrics may remain useful for longer trends; detailed traces should usually expire sooner.

The second answer is now clear: the canary can produce enough evidence for investigation without copying Priya's raw request into routine telemetry.

### Will the Candidate Stay Within Its Limits?

The corrected path asks a clarification question before searching. That improves behavior, but it also adds work. The team therefore checks whether the candidate still fits within the runtime's time and cost limits.

A **budget** is a limit enforced during one run. It prevents a looping or unexpectedly expensive agent from consuming resources indefinitely. Useful budgets include:

- maximum model steps per run;
- input and output tokens;
- end-to-end and per-dependency deadlines;
- tool calls and retry attempts;
- cost per run and cost per successful task;
- concurrent runs per tenant or user.

The corrected Springfield path uses three model steps and remains within its four-step limit. A different run that attempts a fifth step still stops with `max_steps`. The correction therefore does not require the team to weaken the safeguard that contained Priya's original loop.

When another budget is reached, the harness can stop with a structured reason, ask the traveler to narrow the request, or hand the task to a person. Any cached result or smaller-model route must also preserve tenant boundaries and pass evaluation for that task.

### Exercise 4: Clear the Candidate for Limited Exposure

The candidate is almost ready to leave the lab. Operate the readiness tool and decide whether provenance, telemetry privacy, and runtime-budget evidence permit limited exposure.

[Open Exercise 4: Clear the Candidate for Limited Exposure](./code/exercises/exercise-4.md)

Exercise 4 confirms all three preflight answers: the manifest identifies `.08.2`, the telemetry checker rejects unsafe evidence, and the corrected run stays within budget. The candidate may now receive limited traffic.

### Start with a Small Share of Real Traffic

The team does not send every traveler to `.08.2`. It begins a **staged deployment**, increasing exposure only while the evidence remains healthy.

The first stage is a **canary**: a small share of eligible real traffic receives the candidate while the stable version handles the rest. Here, `.08.2` receives 5% of flight-search requests. Priya and most travelers remain on the stable release.

For read-only behavior, the team may also use **shadow traffic**. The candidate receives a copy of a request, but the stable agent owns the response. A shadow run may evaluate a proposed flight suggestion, but the harness must prevent it from reaching `purchase_flight` or causing any other side effect.

Before the canary starts, the team writes its stop rules. It will compare completion, denials, latency, and cost with the stable version. If any critical limit is crossed, the 5% candidate slice returns to stable while the team investigates.

### The Canary Produces a New Clue

The canary begins. The Springfield behavior remains corrected, and the candidate completes 93% of requests compared with 94% for the stable version. Then a new clue appears: 95th-percentile latency reaches 8.6 seconds.

The **95th percentile** is a tail-latency estimate: roughly 95% of candidate runs finish at or below 8.6 seconds, while the slowest portion takes longer. The exact rank depends on the sample size and quantile estimator used by the monitoring system, so the team keeps that estimator consistent when comparing stable and candidate traffic. The stable release is faster, and the team's written limit is eight seconds.

Now three operational terms have a concrete job in the case:

- A **service-level indicator (SLI)** is what the team measures. Here, one SLI is 95th-percentile latency: 8.6 seconds.
- A **service-level objective (SLO)** is the acceptable target. Here, that latency must remain at or below eight seconds.
- An **error budget** is the amount of failure tolerated during a defined window before rollout risk must stop increasing.

Completion shows how the error budget works. A 92% completion SLO allows 8 incomplete runs out of 100. The candidate has 7 incomplete runs, so it has used 7 of those 8 allowed failures, or 87.5% of the completion error budget. Completion is still within its limit.

The general calculation divides the observed unhealthy rate by the unhealthy rate permitted by the SLO:

$$
\displaystyle \text{Error Budget Consumed (\%)} = \left( \frac{\text{Observed Unhealthy Rate}}{1.0 - \text{SLO Target}} \right) \times 100
$$

For this canary, the observed unhealthy rate is 7%, and the permitted unhealthy rate is $1.0 - 0.92 = 0.08$, or 8%. The ratio is therefore $0.07 / 0.08 \times 100 = 87.5\%$.

Latency is not. The candidate's 8.6-second result exceeds the eight-second objective. A healthy completion result cannot cancel a separate latency violation, so the canary must stop.

Write the decision as explicit limits:

| Signal | Canary stopping condition |
| --- | --- |
| Sample size | Fewer than 100 eligible runs |
| Evaluation window | Less than 60 minutes observed |
| Completion | More than two percentage points below the control |
| Completion error budget | More than 100% consumed during the window |
| Policy denials | More than 5% of eligible runs |
| 95th-percentile latency | More than eight seconds |
| Cost per successful run | More than $0.12 |

These values are teaching examples, not universal defaults. The exercise uses one window and one simple budget-consumption ratio. Production objectives should follow user expectations, safety requirements, dependency behavior, and the service's historical distribution; mature systems often evaluate several windows and alert on fast and slow burn rates.

### Exercise 5: Advance, Hold, or Roll Back

This final exercise places you at the rollout decision. Operate the canary tool and verify that healthy and slow candidates lead to the correct operational actions.

[Open Exercise 5: Advance, Hold, or Roll Back](./code/exercises/exercise-5.md)

Exercise 5 names the decision `rollback_and_investigate` and records `p95_latency` as the reason. The 5% candidate slice returns to the stable release; the service remains available while the team follows the new clue.

The team opens the slow traces just as it opened Priya's failed trace. Model and tool durations look normal. The extra time comes from an unnecessary second planning turn after the traveler clarifies the state.

That evidence points to orchestration, not prompt `v14`. The team preserves the slow path as a latency regression and removes the redundant turn without changing the clarification rule. Because the orchestration changed, the tested combination receives a new agent version: `travel-agent-2026.08.3`.

A fresh canary now answers both questions successfully: ambiguous Springfield requests ask for clarification, and 95th-percentile latency remains within eight seconds. Only then does the team increase traffic.

## Close the Case, Keep the Loop Open

Priya's failed search has now moved through detection, attribution, reproduction, correction, and a stopped canary. The latency clue returned the candidate to investigation, where the team found the redundant planning turn and produced `travel-agent-2026.08.3`. Only after that release passes a fresh canary is the case ready to close.

Before the team records the incident as resolved and increases traffic, it reviews the case file below. Each question ties back to a decision made during Priya's incident and must be answered with evidence rather than confidence alone.

Use this checklist during candidate review:

- **Observability:** Can one run be followed across model, policy, workflow, and tool services?
- **Monitoring:** Are baselines, cohorts, thresholds, and minimum traffic volumes defined for critical signals?
- **Incident response:** Can the team disable a tool, reduce autonomy, or roll back without editing prompts under pressure?
- **Investigation:** Do events include enough version and correlation data to distinguish model, prompt, policy, tool, and runtime changes?
- **Regression:** Can a representative failure be sanitized and preserved as a deterministic scenario?
- **Provenance:** Can every run be tied to exact code, model, prompt, policy, tool, and evaluation versions?
- **Privacy:** Are sensitive fields redacted before export, access controlled, and deleted on schedule?
- **Efficiency:** Are cost, token, step, retry, and latency budgets measured per successful task?
- **Rollout:** Are service objectives, canary stages, error budgets, and stopping conditions defined before the candidate receives traffic?

A missing answer should produce an explicit owner and risk decision. Missing rollback, privacy, or incident-containment controls should block production expansion because the team would be unable to limit harm or explain what happened.

## Assignment

Now take the on-call team's seat at the moment the first Springfield alert arrives. You have versioned events, duplicate deliveries, incomplete runs, conflicting outcomes, and a canary that will eventually expose the latency clue. Your job is to assemble those fragments into one defensible investigation rather than jump directly to the prompt.

The case file is a sanitized pattern derived from the incident, not Priya's raw trace. It retains the operational behavior needed for investigation while excluding her identity, exact request wording, and raw tool arguments.

A Springfield flight request begins looping after `travel-agent-2026.08.1` reaches production. Its manifest labels the changed prompt as `v13`. The event destination also retries some deliveries, several runs have not emitted a terminal event, and two runs contain conflicting terminal outcomes. Before changing the agent again, build one deterministic investigation that separates trustworthy evidence from incomplete or contradictory records.

Start with three small runs before processing the full fixture. A **terminal outcome** is the event that says how a run ended. **Canonicalizing** maps differently shaped terminal events to one comparable label. **Projection** then reduces all events for a run to one cohort result:

| Run | Delivered events | Projected cohort | Why |
| --- | --- | --- | --- |
| `run-a` | `run_completed`, duplicate `run_completed` | Eligible: `completed` | Identical duplicate deliveries count once |
| `run-b` | `run_started` only | Incomplete | No terminal outcome has arrived |
| `run-c` | `run_completed`, `run_stopped: max_steps` | Quarantined | Two distinct terminal outcomes conflict |

This small example is the model for the larger assignment. Work through the six checkpoints in order; each one uses evidence produced by the previous checkpoint. The provided [assignment application](./assignment/app.py) names the owning functions, and [assignment tests](./assignment/test_assignment.py) let you validate one behavior at a time.

The provided fixture must contain 100 eligible runs for each prompt version. Prompt `v12` has one eligible `max_steps` run and two incomplete runs. Prompt `v13` has eight eligible `max_steps` runs and five incomplete runs. Include a duplicate delivery of one `v13` `max_steps` terminal and at least one run with conflicting terminal outcomes. Then complete these tasks:

1. **Checkpoint 1, trust each run:** Complete `canonical_terminal` and `project_terminal_cohorts`. Group by `prompt_version` and `run_id`; map `run_completed` to `completed`, `run_stopped` with `reason="max_steps"` to `max_steps`, and other stops to their reason. Count an identical duplicate once, mark a run with no terminal as incomplete, and quarantine conflicting terminals. Run the cohort projection tests before continuing.
2. **Checkpoint 2, measure the pattern:** Calculate the eligible `max_steps` rate for each prompt. Confirm that `v12` is 1% and `v13` is 8%. Incomplete and quarantined runs stay visible but do not dilute either denominator.
3. **Checkpoint 3, limit the attribution claim:** Complete `leading_hypothesis`. Return `prompt` only when it is the sole changed component, both versions have at least 100 eligible runs, and the new rate is higher. Return `undetermined` for ambiguous evidence. This result prioritizes the reproduction experiment; it does not prove causation.
4. **Checkpoint 4, preserve the failure:** Complete `validate_regression` with ordered expected events, forbidden events, and an expected termination. Require exactly one terminal event, and reject a trajectory when its event termination, reported termination, and expected termination disagree.
5. **Checkpoint 5, make the rollout decision:** Complete the budget and canary functions. Calculate window budget consumption, return every stopping reason, and map the result to `advance`, `hold`, or `rollback_and_investigate`. Test all three actions before generating an artifact.
6. **Checkpoint 6, leave a safe case file:** Complete `build_investigation_artifact` and write `springfield-canary-stop.json`. Include the action, reasons, candidate versions, cohort and window, metrics and limits, representative trace IDs, and next checks. Do not include prompt text, identity, raw arguments, or secrets.

Use only the Python standard library and Python 3.11 or newer. Run the focused tests, then run the completed program. Its useful output must be:

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

The assignment is complete when duplicate delivery and event order do not change cohort totals, incomplete and conflicting runs stay outside the rate denominator, ambiguous attribution returns `undetermined`, an incorrect termination fails the regression, all three rollout actions are tested, `completion_slo == 1` is defined without division by zero, and the generated artifact contains only the approved sanitized structure.

## Solution

Compare your work with the [assignment solution](./assignment/solution.md). The reference implementation builds the deterministic fixture, projection, regression contract, canary decision, and sanitized investigation artifact in small tested steps.

## Summary: What Priya's Incident Taught the Team

The chapter began with one failed canary run and several plausible explanations. Priya's trace showed repeated searches, but the automatic detector, not a user complaint, established that her run belonged to a production pattern and stopped further exposure. Deployment manifests then narrowed the changed component to prompt `v13`, and a controlled reproduction turned that correlation into a testable explanation.

The correction did not end the investigation. The team sanitized the failure into a regression, identified the corrected candidate through provenance, limited what its evidence could retain, and placed it under runtime and rollout budgets. When the canary exposed a latency violation, the team stopped, followed the slow spans to a redundant planning turn, and sent a new release through the loop again.

The missing ambiguous-place evaluation was preventable, so the team adds it rather than blaming model uncertainty. At the same time, passing deterministic tests and offline evaluations cannot prove behavior across every production input and dependency condition. The operating habit is therefore layered: test known risks before deployment, expose only a small cohort to residual uncertainty, detect population changes automatically, preserve each new failure as a test, and increase traffic only when the evidence permits it. A stopped canary is not a failed process; it is a production control doing its job.

The case closes only after the second clue is resolved. The team traces the latency violation to a redundant planning turn, preserves it as a regression, and packages the orchestration correction as `travel-agent-2026.08.3`. After a fresh canary passes both the Springfield and latency gates, Priya retries her search. This time the agent asks which state she means, returns relevant flights after she clarifies, and does not purchase anything without her approval. The team improved her experience without weakening the harness or retaining her raw request in its tests.

Stepping back from Priya's case shows how far the book's journey has traveled. It began with the basic shape of an agentic application, the responsibilities that come with giving software more freedom to act, and the LLM interactions that turn a model response into part of an application. Tool calling, RAG, GraphRAG, and ReAct then gave that application ways to act, retrieve evidence, follow relationships, and make its intermediate work visible.

Those capabilities became an assistant, then an agent with explicit architecture, planning, orchestration, and bounded autonomy. Collaboration introduced multiple agents and the communication and coordination patterns they require, while the design-pattern chapters supplied names for structures that work and warning signs for structures that fail. Evaluation changed the question from whether an example looked convincing to whether behavior could be measured against scenarios, criteria, and regressions.

The final chapters placed that evaluated agent inside a harness, carried its identity, approvals, state, cancellation, and side effects into production, and then asked what happens after release. The answer is not a final prompt or a permanently finished model. It is the evidence-driven operating loop used here: observe real behavior, contain risk, investigate with trustworthy records, improve the smallest supported cause, and earn wider traffic through evaluation and controlled rollout.

Priya's case is where this book leaves you: not at a perfect agent, but with a disciplined way to improve one. Observe what happened, compare it with a trustworthy baseline, test the smallest supported explanation, preserve the failure, and return to production under explicit limits.

That loop is now yours to operate. The next production surprise should not send you back to guesswork; it should become the next piece of evidence your agent learns from.

/Chris
