# Exercise 2 Solution: Predict Failure

## Problem
For the same Copenhagen booking workflow, identify likely anti-pattern failures early and define concrete refactors.

## What is required vs optional

Minimum required for Exercise 2:

- Identify at least three anti-pattern risks.
- For each risk, provide one observable symptom, one likely root cause, and one concrete refactor.

## How this solution was created

We built this solution with a simple three-step method:

1. Predict the top ways the workflow can fail.
2. Tie each failure to a specific root cause.
3. Add one concrete engineering control for each failure.

### How to answer with this method

For each risk, use this exact response pattern:

- Symptom -> what you can observe when the failure happens.
- Likely root cause -> the specific design reason the symptom occurs.
- Concrete refactor -> the engineering control that fixes or reduces that risk.

## Solution

Here are the risks we've identified for the Copenhagen booking workflow, along with their symptoms, root causes, and concrete refactors.

### Risk 1: Unbounded autonomy
- Symptom: planner keeps generating additional search/refinement steps without converging.
- Likely root cause: no max-iteration or token budget constraints on the planner loop.
- Concrete refactor: enforce hard limits (`max_iterations=5`, token budget cap), plus explicit stop conditions (`policy_satisfied`, `budget_exceeded`, or `no_better_option_found`).

### Risk 2: Tool roulette
- Symptom: near-identical prompts trigger different tool sequences and produce inconsistent recommendations.
- Likely root cause: fuzzy routing rules and missing tool eligibility checks.
- Concrete refactor: introduce deterministic routing by intent class (retrieve/analyze/policy/execute), validate required inputs per tool, and reject ineligible tool calls before execution.

### Risk 3: Hidden state coupling
- Symptom: a change in one step (for example hotel preference write) unexpectedly alters downstream flight ranking behavior.
- Likely root cause: mutable shared state without explicit contracts between workers.
- Concrete refactor: define typed state contracts, pass immutable step outputs, and isolate worker-local context from shared conversation memory.

### Risk 4: Evaluation last
- Symptom: team debates quality after implementation because pass/fail criteria are unclear.
- Likely root cause: no predefined metrics or thresholds before architecture work began.
- Concrete refactor: define completion, unsafe action, latency, and cost thresholds up front and gate changes against those metrics.

## What comes next

Exercise 2 stops at risk prediction and refactor design.

Defining metrics and building measurement workflows is a separate skill that starts in Chapter 16 (Evaluation).

