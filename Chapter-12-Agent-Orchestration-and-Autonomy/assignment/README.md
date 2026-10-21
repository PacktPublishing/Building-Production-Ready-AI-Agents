# Chapter 12 Assignment - Resumable Travel Workflow

This assignment turns the chapter ideas into one concrete system: a travel-booking workflow that can collect intent, apply policy, pause for approval, save a checkpoint, and resume later. The point is not to build a giant agent. The point is to make the control decisions visible and testable.

Chapter 11 asked you to reason about planner, executor, and monitor roles inside one planning loop. Chapter 12 adds a second layer of responsibility: workflow shape, decision authority, recovery, and traceability across a multi-step run.

## What this assignment covers

This assignment is intentionally small so you can read the whole system without losing the thread. Even so, it demonstrates the core Chapter 12 concerns in one place.

- **Workflow orchestration**: the app moves through intent collection, quote estimation, policy review, approval, resume, and booking.
- **Autonomy control**: low-risk runs complete automatically, while higher-cost runs stop at an approval gate.
- **Checkpoint recovery**: the app saves a durable JSON snapshot before the approval pause so the run can continue later.
- **Observability**: every important decision is appended to a trace so you can inspect what happened and why.

Before you open the code, keep one framing idea in mind: the workflow is deterministic on purpose. That lets you focus on control flow and ownership instead of model behavior.

## File map

The implementation is split into a few small modules so each responsibility stays easy to inspect. That matters in this chapter because hidden control flow is exactly what we are trying to avoid.

- **app_models.py**: session state, policy config, quote summary, trace event, and API request/response models.
- **checkpoint_store.py**: JSON checkpoint persistence for save and restore.
- **orchestration.py**: request parsing, quote generation, policy routing, approval handling, resume behavior, and response assembly.
- **webapp.py**: FastAPI routes and static file serving.
- **main.py**: compatibility entrypoint for `uvicorn`.
- **static/index.html** and **static/app.js**: a minimal browser UI for creating sessions, sending requests, approving, denying, and resuming.
- **tests/test_assignment.py**: focused tests for approval, denial, checkpoint restore, and autonomous completion.

Now that you know the moving pieces, the next question is why this shape matters for the chapter.

## Why this assignment matters

The assignment is built around one teaching goal: orchestration and autonomy only become real when you can point to the exact place where a run paused, the exact state that was saved, and the exact reason it resumed. A lot of examples talk about those ideas. This one makes them concrete.

Here is the practical flow you should expect:

1. The user sends a travel request.
2. The planner fills in structured state from that message.
3. The workflow estimates quotes and saves a checkpoint.
4. The monitor decides whether to block, continue automatically, or require approval.
5. If approval is granted, the run resumes from the saved checkpoint and completes booking.

That checkpoint-and-resume handoff is the center of the assignment. Without it, approval would just be another boolean gate. With it, the run demonstrates durable recovery and resumability.

## Run the app

From this folder, install dependencies first. Once the environment is ready, start the FastAPI server and open the browser UI.

```bash
uv sync
uv run uvicorn main:app --reload --port 8014
```

Open:

Open the browser at [http://127.0.0.1:8014/](http://127.0.0.1:8014/).

As soon as the page loads, create a session and send a request such as `Book a trip to Tokyo next month with budget 1800 for 2 travelers`.

If you want one concrete first pass, use that exact request, watch the workflow pause at approval, approve it, and then resume from checkpoint. That single run exercises the main teaching path of the assignment from end to end.

## What to try

The fastest way to understand the assignment is to force the workflow down different control paths. That lets you compare autonomy and recovery behavior using the same interface.

- **Autonomous path**: use a smaller trip request so the total stays under the approval limit and the run completes without a pause.
- **Approval path**: use a larger request so the quoted total crosses the approval limit, then approve it and resume from checkpoint.
- **Denial path**: trigger the approval gate again, but deny it and verify that booking never runs.
- **Blocked path**: raise the budget or policy so the quoted total reaches the hard stop threshold and confirm that the workflow refuses to continue.

As you do that, keep the trace panel open. The trace is where the chapter’s later sections become tangible.

## Test the assignment

The tests are intentionally narrow and behavior-focused. They check the exact control points the chapter cares about instead of trying to cover every branch in the UI.

```bash
uv run --with pytest pytest -q
```

The tests cover four critical outcomes:

- **Approval required**: the run pauses and saves a checkpoint.
- **Approval denied**: the run stops before booking.
- **Approval granted plus resume**: the saved checkpoint restores and the run finishes.
- **Autonomous completion**: a low-risk request completes without manual intervention.

## Suggested study questions

Once the scaffold is running, it is worth pausing before you change code. The most useful learning usually comes from naming what the system is already doing clearly.

- **Checkpoint boundary**: why is the checkpoint saved after quote estimation instead of only after approval?
- **Authority boundary**: what exactly changes when the run moves from `awaiting_approval` to `ready_to_resume`?
- **Trace quality**: which trace events would help most if a user asked why booking did not happen?
- **Extension path**: if you added retries or parallel quote fetching, where would that logic belong without breaking the current boundaries?

Those questions set up the natural next step: extending the scaffold without destroying the separation between orchestration, policy, and execution.

