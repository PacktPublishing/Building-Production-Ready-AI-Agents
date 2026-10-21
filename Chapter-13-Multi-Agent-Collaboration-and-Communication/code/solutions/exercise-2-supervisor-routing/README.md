# Exercise 2: Supervisor Routing

This exercise shows how a message envelope gets routed to the correct agent. It is a small routing demo, not a full travel-planning system.

The key idea is simple: when a message arrives, the coordinator inspects the envelope and chooses the agent that should actually do the work.

## What This Demos

This script demonstrates message validation and routing across three example messages:

- a request from planner to researcher,
- a plan review from researcher to policy,
- and a revision request from policy back to planner.

Typical message envelope:

```python
Message(
	trace_id="trip-2048",
	from_agent="planner",
	to_agent="researcher",
	type="request",
	payload={"goal": "book Copenhagen trip", "constraints": ["budget < 2200"]},
)
```

This message routes to `researcher` because the `type` is `request` and the destination agent is `researcher`.

## Why It Matters

Routing keeps the team coordinated. It ensures the planner plans, the researcher researches, the policy agent reviews, and the coordinator sends work to the right place.

## Prerequisites

- Python available on your machine.

## Run

From the `code/` folder, run:

```bash
python solutions/exercise-2-supervisor-routing/solution.py
```

The solution is in [solution.py](solution.py).

## Expected Output

You should see one trace line per input message. Each line includes:

- the shared `trace_id`,
- the sender and receiver,
- the message type,
- and the routed next agent.

For example, a `request` message sent to `researcher` routes to `researcher` because the envelope is explicit and valid. A `plan_review` to `policy` routes to `policy` for the same reason.

If you change `type` or `to_agent`, the routed agent can change. If the envelope is invalid, validation fails before routing.