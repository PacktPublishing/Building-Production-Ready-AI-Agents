# Exercise 5: Peer-to-Peer Pattern

## Premise

This exercise implements direct negotiation between two peer agents with conflicting priorities.

A cost-focused negotiator and an experience-focused negotiator exchange offers until they converge on agreement or hit timeout.

Why this matters: Peer-to-Peer is the right fit when no single coordinator should unilaterally decide and the core task is negotiation.

## Run Instructions

From this folder:

```bash
python solution.py
```

## Expected Output

You should see output headers/signals like:

- `[Negotiation] Cost Agent vs Experience Agent`
- `Initial positions:`
- `[Round 1]` (and potentially later rounds)
- `Negotiation Result:` JSON block

Expected behavior:

- JSON includes:
  - `status` (`AGREEMENT` or `TIMEOUT`)
  - `summary`
  - `agreed_total` (if agreement)
  - `rounds`
- If no agreement is reached within max rounds, output indicates escalation/timeout.
