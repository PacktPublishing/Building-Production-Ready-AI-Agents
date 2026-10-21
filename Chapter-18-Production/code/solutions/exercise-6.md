# Exercise 6 Solution: Reconcile an Uncertain Purchase

This solution handles purchases whose responses were lost. The application does not retry blindly; it uses the airline's answer to decide whether the action is retryable or already completed.

## Follow the Action Record

The cumulative `Agent.invoke_tool` now claims and completes side effects. The [starter](../exercises/exercise-6.py) asks you to add `Agent.reconcile_action`, then the scenario moves one action through these transitions:

1. Claim `purchase-FL-204-user-1842` with its action fingerprint.
2. Mark the result `status_unknown` after the response disappears.
3. Use the airline's "no booking" response to mark it `retryable`.
4. Claim a new `started` attempt with the same idempotency key.
5. Mark its missing response `status_unknown`.
6. Use the airline's booking record to mark it `completed`.

The idempotency key says that each step refers to one intended purchase. The fingerprint prevents that key from being reused for another tool or flight.

## Open the Runnable Version

Open [exercise-6.py](./exercise-6.py) to see the complete transition through the temporary durable store.

## Prepare the Local Run

This exercise requires Python 3.11 or newer and [`uv`](https://docs.astral.sh/uv/). Prepare the shared environment:

```powershell
cd Chapter-18-Production/code
uv sync
```

This deterministic exercise does not require Ollama.

## Reconcile the Purchase

```powershell
uv run python solutions/exercise-6.py
```

Expected output:

```text
Action status: started
Action status: status_unknown
Action status: retryable
Action status: completed
Reconciled action: Purchased FL-204 for user-1842
```

## What You Proved

A missing response is not proof that the airline rejected or completed the purchase. Only the airline's explicit "no booking" response permits a retry. Its later booking record changes the action to `completed` and provides the durable result.
