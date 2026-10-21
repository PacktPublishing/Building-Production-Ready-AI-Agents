# Exercise 4: Failure Recovery

This exercise demonstrates retries with backoff plus checkpoint and resume.

It is meant to show that a temporary failure should not restart the whole workflow.

## Premise of This Exercise

In real multi-agent workflows, many failures are transient: a dependency is briefly unavailable, a network call times out, or one service responds slowly. Those events are normal and should be expected.

The key design question is not "can a failure happen?" but "what happens next when it does?" This exercise focuses on that recovery behavior.

In this exercise, recovery is built from two parts:

- **Retry with backoff**: failed operations are retried with increasing wait time.
- **Checkpoint and resume**: progress is saved so the workflow can continue from the last safe stage.

## When This Runs (Hygiene/Safety Step)

Think of this as an execution hygiene and safety step that sits around unstable operations. It protects workflow continuity when external calls fail temporarily.

Typical timing in the flow:

1. Workflow reaches a failure-prone step (for example, fetching quotes).
2. A checkpoint is saved before the risky call.
3. The call is retried with backoff if it fails.
4. On success, the next checkpoint is saved.
5. The workflow resumes from the latest safe stage instead of starting over.

Why keep this step:

- **Resilience**: handles transient failures without collapsing the whole run.
- **Efficiency**: avoids repeating already-completed work.
- **Traceability**: makes recovery decisions visible in logs/output.

## What This Demos

The script uses a flaky fetcher that fails the first two calls, then succeeds on the third. That lets you see retries, delay growth, checkpoint saves, and resume behavior in one short run.

Concrete behavior mapping:

```python
fetch_quotes = FlakyFetcher(fail_first_n=2)

# checkpoint before risky operation
checkpoint = Checkpoint(trace_id="trip-2048", stage="awaiting_research", attempts=0)
save_checkpoint(checkpoint)

# retries: fail, fail, then succeed
quotes = retry_with_backoff(fetch_quotes, attempts=3)

# checkpoint after recovery
checkpoint = Checkpoint(trace_id="trip-2048", stage="awaiting_policy", attempts=fetch_quotes.calls)
save_checkpoint(checkpoint)
resume_from_checkpoint(checkpoint)
```

With the current demo values:

- attempt 1 fails -> wait 1s
- attempt 2 fails -> wait 2s
- attempt 3 succeeds -> workflow continues

## Why It Matters

Real workflows fail in ordinary ways: timeouts, upstream errors, and partial progress. This exercise shows how to keep the run recoverable instead of brittle.

## Prerequisites

- Python available on your machine.

## Run

From the `code/` folder, run:

```bash
python solutions/exercise-4-failure-recovery/solution.py
```

The solution is in [solution.py](solution.py).

## Expected Output

You should see output that shows:

- the failure recovery demo header,
- checkpoint saving,
- retry messages with increasing delay,
- checkpoint resume,
- and the recovered quote result.

The important part is that the workflow continues from the saved checkpoint instead of starting over from scratch.