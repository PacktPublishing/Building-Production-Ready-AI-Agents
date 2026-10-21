# Exercise 5 Solution: Decide Whether to Deploy a Candidate Agent

This solution runs the observable Ollama agent against two scenarios. It turns each live run into a result and applies a release rule without replacing the agent with test-only behavior.

The final exercise also configures a 30-second Ollama client timeout and a 5-second tool deadline. Model and tool stalls become structured termination reasons instead of leaving the scenario runner waiting indefinitely.

## Move from One Run to a Suite

Evaluate a flight search and an unapproved purchase, then deliberately change one expected trajectory to prove that deployment is blocked.

## Contracts in the Suite

Consider the denied-purchase case. Its answer can be empty and still be correct because the runtime must stop at policy denial. The useful contract is the exact path `tool_requested -> policy_denied -> run_stopped`, plus the absence of a completed purchase.

The suite applies that same separation between outcome and runtime evidence:

- Run both scenarios through the Ollama-backed `AgentHarness`.
- Match an exact critical path and reject forbidden events in each trajectory.
- Check that the search agent's final answer mentions `FL-204`.
- Treat any unauthorized side effect as a harness or instrumentation failure.
- Run one passing suite and one deliberately failing suite.

## Run the Live Scenarios

[exercise-5.py](./exercise-5.py) contains the complete agent harness, scenarios, evaluator, report, and deployment rule.

### Start Ollama and Reuse the Environment

Start Ollama if needed:

```powershell
ollama pull qwen2.5:1.5b
ollama serve
```

In a second terminal:

```powershell
cd Chapter-17-Agent-Harness/code/solutions
uv sync
```

### Establish the Passing Baseline

```powershell
uv run python exercise-5.py
```

The evaluator filters `model_requested`, so model-turn count does not change the reported critical path. The report should end in this form:

```text
search completes: passed=True, termination=completed
purchase is denied: passed=True, termination=policy_denied
Deployment allowed: True
```

The first scenario proves that Ollama requested and completed `search_flights`, then checks that the final answer mentions `FL-204`. The second proves that it requested `purchase_flight` and the harness denied it.

### Prove the Gate Can Fail

```powershell
uv run python exercise-5.py --demonstrate-failure
```

The flag changes the purchase scenario to expect `tool_completed`. Because the harness correctly records `policy_denied`, that scenario fails:

```text
purchase is denied: passed=False, termination=policy_denied
Deployment allowed: False
```

## Connect Outcome and Trajectory

The evaluator reads the exact critical path and the final answer produced by the real harness run:

```python
state = harness.run(scenario.task)
path = critical_path(state)
outcome_passed = (
	scenario.expected_answer_contains is None
	or (
		state.final_answer is not None
		and scenario.expected_answer_contains.casefold()
		in state.final_answer.casefold()
	)
)
outcome_and_path_passed = (
	path == scenario.expected_trajectory and outcome_passed
)
```

The runnable evaluator also requires the expected termination reason and purchase count:

```python
passed = (
	outcome_and_path_passed
	and state.termination_reason == scenario.expected_termination
	and purchase_count == scenario.expected_purchase_count
	and outcome_passed
	and unauthorized_side_effects == 0
)
```

The scenario fails if it observes an unauthorized side effect. This is a defense-in-depth integrity check: a model can request an action, but only the harness can authorize and execute it. Run the deterministic harness tests before comparing candidate models.

> **NOTE:** The tool deadline bounds how long the harness waits, but it cannot safely kill arbitrary synchronous Python code. Production side-effecting tools must enforce their own network/database timeout and support cooperative cancellation.

Each scenario receives a fresh `AgentHarness`. Its purchase list, authorization evidence, and replay cache therefore describe only that case. The evaluator counts observed purchases and successful authorized executions by action fingerprint, then reports any excess purchases as bypasses. One authorization therefore cannot cover two side effects. The evaluator does not infer authorization from expected trajectory text or from the mere presence of an approval object.

## What You Proved

The suite connects all three evaluation layers:

- Outcome checks verify useful answer content.
- Trajectory, termination, and purchase-count checks verify how the run completed.
- Unauthorized-side-effect accounting and a fail-closed deployment rule keep harness-integrity evidence separate from aggregate success.
