# Exercise 4: Committee Pattern

## Premise

This exercise models governance-style decision making with a Committee pattern.

Multiple role-based members discuss options, cast weighted votes, and produce a final decision with dissent captured.

Why this matters: Committee makes approval flow explicit and preserves minority viewpoints for auditability.

## Run Instructions

From this folder:

```bash
python solution.py
```

## Expected Output

You should see output headers/signals like:

- `[Committee] Trip Decision Discussion`
- `[Committee] Starting discussion...`
- Member sections such as `[Policy Agent]`, `[Cost Agent]`, etc.
- `[Committee] Vote tally:`
- `Committee Decision:` JSON block

Expected behavior:

- JSON includes:
  - `final_decision`
  - `vote_breakdown`
  - `dissenting_votes`
- Dissent entries include member rationale and concerns.
