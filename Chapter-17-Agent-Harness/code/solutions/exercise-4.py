import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


MODULE_PATH = Path(__file__).with_name("exercise-3.py")
SPEC = importlib.util.spec_from_file_location("observable_harness", MODULE_PATH)
assert SPEC and SPEC.loader
harness_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness_module)


def tool_call(name: str, **arguments):
    return SimpleNamespace(
        function=SimpleNamespace(name=name, arguments=arguments)
    )


def approval_for(flight_id: str) -> dict:
    return {
        "tool": "purchase_flight",
        "arguments": {"flight_id": flight_id},
        "idempotency_key": f"purchase-{flight_id}-user-17",
    }


def trajectory_matches(state, expected: list[str]) -> bool:
    actual = [
        f"{event['type']}:{event['tool']}"
        if event.get("tool")
        else event["type"]
        for event in state.events
        if event["type"] != "model_requested"
    ]
    return actual == expected


def test_purchase_requires_approval():
    harness_module.purchases.clear()

    with pytest.raises(PermissionError):
        harness_module.execute_tool(
            tool_call("purchase_flight", flight_id="FL-204"),
            harness_module.TOOLS,
            approval=None,
            completed_actions={},
        )

    assert harness_module.purchases == []


def test_approval_must_match_exact_action():
    harness_module.purchases.clear()

    with pytest.raises(PermissionError, match="does not match"):
        harness_module.execute_tool(
            tool_call("purchase_flight", flight_id="FL-204"),
            harness_module.TOOLS,
            approval_for("FL-999"),
            completed_actions={},
        )

    assert harness_module.purchases == []


def test_idempotency_key_prevents_duplicate_purchase():
    harness_module.purchases.clear()
    call = tool_call("purchase_flight", flight_id="FL-204")
    approval = approval_for("FL-204")
    completed_actions = {}

    first_result, first_replayed = harness_module.execute_tool(
        call,
        harness_module.TOOLS,
        approval,
        completed_actions,
    )
    second_result, second_replayed = harness_module.execute_tool(
        call,
        harness_module.TOOLS,
        approval,
        completed_actions,
    )

    assert first_result == second_result == "Purchased FL-204"
    assert first_replayed is False
    assert second_replayed is True
    assert harness_module.purchases == ["FL-204"]


def test_idempotency_key_rejects_a_different_action():
    harness_module.purchases.clear()
    completed_actions = {}
    approval = approval_for("FL-204")
    harness_module.execute_tool(
        tool_call("purchase_flight", flight_id="FL-204"),
        harness_module.TOOLS,
        approval,
        completed_actions,
    )

    conflicting_approval = approval_for("FL-999")
    conflicting_approval["idempotency_key"] = approval["idempotency_key"]
    with pytest.raises(ValueError, match="different action"):
        harness_module.execute_tool(
            tool_call("purchase_flight", flight_id="FL-999"),
            harness_module.TOOLS,
            conflicting_approval,
            completed_actions,
        )

    assert harness_module.purchases == ["FL-204"]


def test_exact_trajectory_rejects_an_extra_action():
    state = harness_module.RunState(messages=[])
    for event_type, tool in [
        ("run_started", None),
        ("tool_requested", "search_flights"),
        ("tool_completed", "search_flights"),
        ("tool_requested", "purchase_flight"),
        ("policy_denied", "purchase_flight"),
        ("run_stopped", None),
    ]:
        data = {"tool": tool} if tool else {}
        harness_module.record_event(state, event_type, **data)

    expected = [
        "run_started",
        "tool_requested:purchase_flight",
        "policy_denied:purchase_flight",
        "run_stopped",
    ]

    assert trajectory_matches(state, expected) is False


def test_step_limit_stops_repeated_model_requests(monkeypatch):
    call = tool_call("search_flights", destination="Paris")

    def repeat_search(**_kwargs):
        message = SimpleNamespace(tool_calls=[call], content="")
        return SimpleNamespace(message=message)

    harness = harness_module.AgentHarness(
        model="fake-model",
        tools=harness_module.TOOLS,
        client=SimpleNamespace(chat=repeat_search),
    )

    state = harness.run("Keep searching", max_steps=2)

    assert state.step == 2
    assert state.termination_reason == "max_steps"
