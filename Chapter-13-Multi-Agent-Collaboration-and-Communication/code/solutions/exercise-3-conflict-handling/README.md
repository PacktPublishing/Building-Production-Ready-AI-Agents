# Exercise 3: Conflict Handling

This exercise shows deterministic conflict resolution across competing recommendations.

It is a tiny decision rule, not a planning engine. The script decides whether the plan is accepted or revised when policy or confidence changes the outcome.

## Premise of This Exercise

In many real systems, confidence drives routing. For example, very high confidence might allow automatic progression, while low confidence might route to human review.

In this exercise, the resolver first confirms that the plan has enough structure to arbitrate. It then considers two signals that may disagree about whether the plan should proceed: policy approval (`policy["approved"]`) and evidence strength (`research["confidence"]`).

The conflict appears when those signals point in different directions. For example, policy may say approved while confidence is low, or confidence may be high while policy says not approved.

This function is the tie-breaker for that disagreement. It applies fixed precedence rules and returns a single outcome (`accept` or `revise`).

## When This Runs (Hygiene/Safety Step)

You can think of this as a hygiene and safety checkpoint between initial routing and final execution. It exists to catch contradictory signals before the system acts.

Typical timing in the flow:

1. The planner produces a structured plan with a destination.
2. Initial routing/policy produces a policy signal (`approved`, `approval-needed`, or `blocked`).
3. Research/evidence produces a confidence signal.
4. This conflict resolver checks plan completeness and reconciles disagreements.
5. Only then does the workflow continue to execution or revision.

Why keep this step:

- **Consistency**: avoids acting on mixed signals.
- **Traceability**: gives one explicit rule-based reason for `accept` or `revise`.
- **Safety**: prevents silent progression when policy and evidence disagree.

A common production split looks like this:

- upstream policy/routing layer: decides `approved`, `approval-needed`, or `blocked` using rules, thresholds, and possibly human gates.
- downstream conflict resolver (this exercise): applies deterministic precedence rules to produce a final `accept` or `revise` outcome.

So your proposed premise is valid for a full workflow; this exercise is just focused on one slice of that workflow.

## Why It Matters

A multi-agent system is only useful if disagreement is visible and predictable. This exercise shows that one rule can explain why a plan is revised or accepted.

## What This Demos

The script runs four cases:

- the plan is incomplete,
- policy blocks the plan,
- research confidence is too low,
- and the plan is accepted.

There are three active decision rules in this exercise. The resolver checks for `plan["destination"]` first, then policy approval, and finally whether research confidence is at least `0.7`.

Concrete case mapping:

```python
# Case 1: Missing destination -> revise
plan = {"hotel": "B"}
research = {"confidence": 0.95}
policy = {"approved": True}
# result: {'decision': 'revise', 'reason': 'incomplete plan structure'}

# Case 2: Policy blocks -> revise
plan = {"destination": "Copenhagen", "hotel": "B"}
research = {"confidence": 0.95}
policy = {"approved": False}
# result: {'decision': 'revise', 'reason': 'policy block'}

# Case 3: Low confidence -> revise
plan = {"destination": "Copenhagen", "hotel": "B"}
research = {"confidence": 0.55}
policy = {"approved": True}
# result: {'decision': 'revise', 'reason': 'research too weak'}

# Case 4: Complete plan + policy approved + confidence >= 0.7 -> accept
plan = {"destination": "Copenhagen", "hotel": "B"}
research = {"confidence": 0.90}
policy = {"approved": True}
# result: {'decision': 'accept', 'reason': 'plan is consistent'}
```

Where does `policy["approved"]` come from?

- In this toy script: it is hard-coded per case so you can see rule precedence.
- In a real system: it usually comes from a policy gate, business rules engine, or human approval workflow.
- In this exercise, the resolver only consumes `plan`, `research`, and `policy`, then returns a deterministic outcome.

Typical input shape passed to the resolver:

```python
plan = {"destination": "Copenhagen", "hotel": "B"}
research = {"confidence": 0.55}
policy = {"approved": True}

result = resolve_conflict(plan, research, policy)
# {'decision': 'revise', 'reason': 'research too weak'}
```

## Prerequisites

- Python available on your machine.

## Run

From the `code/` folder, run:

```bash
python solutions/exercise-3-conflict-handling/solution.py
```

The solution is in [solution.py](solution.py).

## Expected Output

You should see four lines of output, one for each case. Each line prints:

- the case name,
- the decision,
- and the reason.

The output should look conceptually like this:

- incomplete plan -> revise
- policy block -> revise
- low confidence -> revise
- consistent plan -> accept

If you remove the destination, change the policy approval flag, or lower the research confidence, the decision changes with it.