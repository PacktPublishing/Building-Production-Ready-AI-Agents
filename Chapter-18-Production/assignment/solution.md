# Assignment Solution: Report Execution and Replay

The exercises already built a production-aware `Agent`. The provided concurrency checkpoint adds the completed two-worker behavior: it can authorize Priya, restore state, protect a side effect with an idempotency key, reconcile uncertainty, and return a durable result to a second worker.

This solution starts from that completed class and adds one final behavior: make execution and replay visible as stable events that survive a temporary publication failure. The assignment does not rebuild any earlier production control.

## Start from the Concurrency Checkpoint

Copy the completed [concurrency checkpoint](../code/checkpoints/08_concurrency.py) into your assignment file. Keep its existing `Agent`, context builder, tool registry, and two-worker scenario unchanged.

Why this matters: the assignment should test whether you can extend the class without weakening its existing guarantees. The purchase must still execute once, and the second worker must still receive the stored result.

## Save an Event Before Publishing It

First, add an `EventSink` parameter to the constructor and store it on the agent. Then introduce `emit_action_event` before changing `invoke_tool`. The method creates the event, attaches it to a small durable state for this action, and saves both through the existing outbox transaction:

```python
def emit_action_event(
    self,
    event_type: str,
    spec: ToolSpec,
    context: RunContext,
) -> None:
    if context.approval is None:
        raise PermissionError("Side effects require an approval")
    event = {
        "event_id": f"event-{uuid.uuid4().hex}",
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant": context.identity.tenant,
        "subject": context.identity.subject,
        "tool_name": spec.name,
        "idempotency_key": context.approval.idempotency_key,
    }
    run_id = f"action-events-{context.approval.idempotency_key}"
    state = self.store.load_checkpoint(run_id) or RunState(
        run_id=run_id,
        messages=[],
        subject=context.identity.subject,
        tenant=context.identity.tenant,
    )
    state.events.append(event)
    self.store.save_event_checkpoint(state, event)
    self.publish_pending_events()
```

The event carries enough context to answer three practical questions:

- Which identity requested the action?
- Which tool and idempotency key identify it?
- Did this call complete the action or replay an earlier result?

Each occurrence receives a unique event ID and timestamp. The correlation fields remain the same across completion and replay so an operator can connect both events to one intended purchase. Most importantly, the event is committed before publication begins.

## Publish Pending Events

Now add the method that drains the outbox. It stops when the sink fails, leaving that event and any later events pending for another attempt:

```python
def publish_pending_events(self) -> None:
    for event in self.store.load_pending_events():
        try:
            self.event_sink.emit(event)
        except Exception:
            return
        self.store.mark_event_published(event["event_id"])
```

Call this method at the start of `execute_tool` as well as after saving a new event. A later request can therefore recover publication without repeating the purchase.

## Emit Both Outcomes

Now make two small additions to `invoke_tool`. Emit `action_replayed` before returning an existing result:

```python
if not claim.execute:
    self.emit_action_event("action_replayed", spec, context)
    return claim.result
```

After the winning worker saves its result, emit `action_completed`:

```python
self.store.complete_action(
    context.identity.tenant,
    context.identity.subject,
    context.approval.idempotency_key,
    claim.generation,
    result,
)
self.emit_action_event("action_completed", spec, context)
return result
```

The placement is intentional. A completion event is emitted only after the durable action record is complete. A replay event is emitted only when the store proves that the provider call should not run again.

## Prepare the Local Run

This assignment requires Python 3.11 or newer and [`uv`](https://docs.astral.sh/uv/). It is deterministic and does not require Ollama to be running.

```powershell
cd Chapter-18-Production/assignment
uv sync
```

## Run the Focused Tests

The tests use `InMemoryEventSink` so they can inspect the two events directly:

```powershell
uv run pytest -q
```

Expected output:

```text
...                                                                      [100%]
3 passed
```

The tests prove that:

- the first and second workers receive the same purchase result;
- the event order is `action_completed`, then `action_replayed`;
- both events contain the required correlation fields; and
- each event has a unique event ID; and
- a completion event remains pending during sink failure and publishes after recovery.

## Inspect the JSON Lines Output

The runnable solution uses `JsonLinesEventSink`. Each call to `emit` appends one JSON object as one line in the event file.

```powershell
uv run python app.py
```

Expected output:

```text
First worker: Purchased FL-204 for user-1842
Second worker replay: Purchased FL-204 for user-1842
Events: action_completed, action_replayed
```

The completed [assignment implementation](./app.py) preserves the concurrency behavior, records the two action outcomes, and routes them through the durable outbox. The purchase remains duplicate-safe even when event publication needs another attempt.