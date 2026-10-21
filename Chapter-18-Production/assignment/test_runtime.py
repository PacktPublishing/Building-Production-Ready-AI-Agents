from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from agent import ApprovalAuthority, DurableStore, InMemoryEventSink
from exercise_support import build_context, build_tools

import app


REQUIRED_FIELDS = {
    "event_id",
    "event_type",
    "timestamp",
    "tenant",
    "subject",
    "tool_name",
    "idempotency_key",
}


def build_agent(tmp_path):
    store = DurableStore(tmp_path / "test.db")
    authority = ApprovalAuthority("test-secret")
    context = build_context(authority)
    sink = InMemoryEventSink()
    agent = app.Agent(authority, build_tools(), store, sink)
    return store, context, sink, agent


def test_completed_and_replayed_actions_emit_correlated_events(tmp_path) -> None:
    store, context, sink, agent = build_agent(tmp_path)
    arguments = {"flight_id": "FL-204"}

    first = agent.execute_tool(
        "purchase_flight", arguments, context, owner="worker-1"
    )
    replay = agent.execute_tool(
        "purchase_flight", arguments, context, owner="worker-2"
    )

    assert first == replay == "Purchased FL-204 for user-1842"
    assert [event["event_type"] for event in sink.events] == [
        "action_completed",
        "action_replayed",
    ]
    assert all(REQUIRED_FIELDS == event.keys() for event in sink.events)
    assert sink.events[0]["idempotency_key"] == sink.events[1]["idempotency_key"]
    assert sink.events[0]["subject"] == sink.events[1]["subject"]
    store.close()


def test_each_event_has_a_unique_id(tmp_path) -> None:
    store, context, sink, agent = build_agent(tmp_path)
    arguments = {"flight_id": "FL-204"}

    agent.execute_tool("purchase_flight", arguments, context, owner="worker-1")
    agent.execute_tool("purchase_flight", arguments, context, owner="worker-2")

    assert sink.events[0]["event_id"] != sink.events[1]["event_id"]
    store.close()


def test_completed_event_survives_sink_failure(tmp_path) -> None:
    class FailingSink:
        def emit(self, event) -> None:
            raise OSError("sink unavailable")

    store = DurableStore(tmp_path / "test.db")
    authority = ApprovalAuthority("test-secret")
    context = build_context(authority)
    agent = app.Agent(authority, build_tools(), store, FailingSink())

    result = agent.execute_tool(
        "purchase_flight",
        {"flight_id": "FL-204"},
        context,
        owner="worker-1",
    )

    assert result == "Purchased FL-204 for user-1842"
    assert [event["event_type"] for event in store.load_pending_events()] == [
        "action_completed"
    ]

    recovered_sink = InMemoryEventSink()
    agent.event_sink = recovered_sink
    agent.publish_pending_events()

    assert [event["event_type"] for event in recovered_sink.events] == [
        "action_completed"
    ]
    assert store.load_pending_events() == []
    store.close()