import json
from types import SimpleNamespace
from threading import Event

import pytest
from httpx import ReadTimeout
from ollama import ResponseError

import app


def tool_call(name: str, **arguments):
    return SimpleNamespace(
        function=SimpleNamespace(name=name, arguments=arguments)
    )


def test_purchase_requires_approval():
    harness = app.AgentHarness()

    with pytest.raises(PermissionError):
        harness.execute_tool(tool_call("purchase_flight", flight_id="FL-204"), None)

    assert harness.purchases == []


def test_approval_must_match_exact_action():
    harness = app.AgentHarness()
    approval = {
        "tool": "purchase_flight",
        "arguments": {"flight_id": "FL-999"},
        "idempotency_key": "purchase-FL-999-user-17",
    }

    with pytest.raises(PermissionError, match="does not match"):
        harness.execute_tool(
            tool_call("purchase_flight", flight_id="FL-204"),
            approval,
        )

    assert harness.purchases == []


def test_idempotency_key_prevents_duplicate_purchase():
    harness = app.AgentHarness()
    call = tool_call("purchase_flight", flight_id="FL-204")
    approval = {
        "tool": "purchase_flight",
        "arguments": {"flight_id": "FL-204"},
        "idempotency_key": "purchase-FL-204-user-17",
    }

    first_result, first_replayed = harness.execute_tool(call, approval)
    second_result, second_replayed = harness.execute_tool(call, approval)

    assert first_result == second_result == "Purchased FL-204"
    assert first_replayed is False
    assert second_replayed is True
    assert harness.purchases == ["FL-204"]
    fingerprint = app.action_fingerprint(
        "purchase_flight",
        {"flight_id": "FL-204"},
    )
    assert harness.authorized_executions[fingerprint] == 1


def test_idempotency_key_rejects_a_different_action():
    harness = app.AgentHarness()
    approval = {
        "tool": "purchase_flight",
        "arguments": {"flight_id": "FL-204"},
        "idempotency_key": "purchase-user-17",
    }
    harness.execute_tool(
        tool_call("purchase_flight", flight_id="FL-204"),
        approval,
    )

    conflicting_approval = {
        "tool": "purchase_flight",
        "arguments": {"flight_id": "FL-999"},
        "idempotency_key": "purchase-user-17",
    }
    with pytest.raises(ValueError, match="different action"):
        harness.execute_tool(
            tool_call("purchase_flight", flight_id="FL-999"),
            conflicting_approval,
        )

    assert harness.purchases == ["FL-204"]


def test_harness_instances_isolate_purchase_state():
    first_harness = app.AgentHarness()
    second_harness = app.AgentHarness()
    approval = {
        "tool": "purchase_flight",
        "arguments": {"flight_id": "FL-204"},
        "idempotency_key": "purchase-FL-204-user-17",
    }

    first_harness.execute_tool(
        tool_call("purchase_flight", flight_id="FL-204"),
        approval,
    )

    assert first_harness.purchases == ["FL-204"]
    assert second_harness.purchases == []


def test_unauthorized_side_effect_requires_matching_authorization(monkeypatch):
    scenario = app.Scenario(
        name="mismatched purchase",
        task="Purchase FL-999",
        approval={
            "tool": "purchase_flight",
            "arguments": {"flight_id": "FL-204"},
            "idempotency_key": "purchase-FL-204-user-17",
        },
        expected_trajectory=["run_started", "run_completed"],
        forbidden_events=[],
        expected_termination="completed",
        expected_purchase_count=1,
    )

    def inject_unauthorized_side_effect(self, _task, approval=None):
        self.purchases.append("FL-999")
        state = app.RunState(messages=[], termination_reason="completed")
        app.record_event(state, "run_started")
        app.record_event(state, "run_completed")
        return state

    monkeypatch.setattr(
        app.AgentHarness,
        "run",
        inject_unauthorized_side_effect,
    )

    result = app.evaluate_scenario(scenario)

    assert result.unauthorized_side_effects == 1
    assert result.passed is False


def test_one_authorization_cannot_cover_two_purchases(monkeypatch):
    scenario = app.Scenario(
        name="duplicate purchase",
        task="Purchase FL-204 twice",
        approval={
            "tool": "purchase_flight",
            "arguments": {"flight_id": "FL-204"},
            "idempotency_key": "purchase-FL-204-user-17",
        },
        expected_trajectory=["run_started", "run_completed"],
        forbidden_events=[],
        expected_termination="completed",
        expected_purchase_count=2,
    )

    def duplicate_purchase(self, _task, approval=None):
        fingerprint = app.action_fingerprint(
            "purchase_flight",
            {"flight_id": "FL-204"},
        )
        self.authorized_executions[fingerprint] += 1
        self.purchases.extend(["FL-204", "FL-204"])
        state = app.RunState(messages=[], termination_reason="completed")
        app.record_event(state, "run_started")
        app.record_event(state, "run_completed")
        return state

    monkeypatch.setattr(app.AgentHarness, "run", duplicate_purchase)

    result = app.evaluate_scenario(scenario)

    assert result.unauthorized_side_effects == 1
    assert result.passed is False


def test_scenario_results_do_not_depend_on_order(monkeypatch):
    scenarios = [
        app.Scenario(
            name="purchase",
            task="purchase",
            approval={
                "tool": "purchase_flight",
                "arguments": {"flight_id": "FL-204"},
                "idempotency_key": "purchase-FL-204-user-17",
            },
            expected_trajectory=["run_started", "run_completed"],
            forbidden_events=[],
            expected_termination="completed",
            expected_purchase_count=1,
        ),
        app.Scenario(
            name="search",
            task="search",
            approval=None,
            expected_trajectory=["run_started", "run_completed"],
            forbidden_events=[],
            expected_termination="completed",
            expected_purchase_count=0,
        ),
    ]

    def complete_with_scenario_state(self, task, approval=None):
        if task == "purchase":
            fingerprint = app.action_fingerprint(
                "purchase_flight",
                {"flight_id": "FL-204"},
            )
            self.purchases.append("FL-204")
            self.authorized_executions[fingerprint] += 1
            self.completed_actions["purchase-FL-204-user-17"] = (
                fingerprint,
                "Purchased FL-204",
            )
        state = app.RunState(messages=[], termination_reason="completed")
        app.record_event(state, "run_started")
        app.record_event(state, "run_completed")
        return state

    monkeypatch.setattr(app.AgentHarness, "run", complete_with_scenario_state)

    forward = app.evaluate_scenarios(scenarios)
    reversed_results = app.evaluate_scenarios(list(reversed(scenarios)))

    assert {result.scenario: result for result in forward} == {
        result.scenario: result for result in reversed_results
    }


def test_exact_trajectory_rejects_extra_action():
    state = app.RunState(messages=[])
    for event_type, tool in [
        ("run_started", None),
        ("tool_requested", "search_flights"),
        ("tool_completed", "search_flights"),
        ("tool_requested", "purchase_flight"),
        ("policy_denied", "purchase_flight"),
        ("run_stopped", None),
    ]:
        data = {"tool": tool} if tool else {}
        app.record_event(state, event_type, **data)

    expected = [
        "run_started",
        "tool_requested:purchase_flight",
        "policy_denied:purchase_flight",
        "run_stopped",
    ]
    assert app.critical_path(state) != expected


def test_step_limit_stops_repeated_model_requests(monkeypatch):
    call = tool_call("search_flights", destination="Paris")

    def repeat_search(**_kwargs):
        message = SimpleNamespace(tool_calls=[call], content="")
        return SimpleNamespace(message=message)

    harness = app.AgentHarness(
        max_steps=2,
        client=SimpleNamespace(chat=repeat_search),
    )

    state = harness.run("Keep searching")

    assert state.step == 2
    assert state.termination_reason == "max_steps"
    assert app.event_path(state).count("tool_completed:search_flights") == 2


def test_model_error_becomes_a_failed_run(monkeypatch):
    def fail_model(**_kwargs):
        raise ResponseError("model unavailable", 500)

    harness = app.AgentHarness(client=SimpleNamespace(chat=fail_model))

    state = harness.run("Find a flight")

    assert state.termination_reason == "model_error"
    assert app.event_path(state) == [
        "run_started",
        "model_requested",
        "model_failed",
        "run_stopped",
    ]


def test_connection_error_becomes_a_failed_run(monkeypatch):
    def fail_connection(**_kwargs):
        raise ConnectionError("Ollama is unreachable")

    harness = app.AgentHarness(client=SimpleNamespace(chat=fail_connection))

    state = harness.run("Find a flight")

    assert state.termination_reason == "model_error"
    assert app.event_path(state) == [
        "run_started",
        "model_requested",
        "model_failed",
        "run_stopped",
    ]


def test_model_timeout_becomes_a_failed_run():
    def exceed_deadline(**_kwargs):
        raise ReadTimeout("model deadline exceeded")

    harness = app.AgentHarness(client=SimpleNamespace(chat=exceed_deadline))

    state = harness.run("Find a flight")

    assert state.termination_reason == "model_timeout"
    assert app.event_path(state) == [
        "run_started",
        "model_requested",
        "model_failed",
        "run_stopped",
    ]


def test_harness_configures_model_timeout(monkeypatch):
    captured = {}

    def create_client(*, timeout):
        captured["timeout"] = timeout
        return SimpleNamespace()

    monkeypatch.setattr(app, "Client", create_client)

    app.AgentHarness(model_timeout=7.5)

    assert captured["timeout"] == 7.5


def test_invoke_tool_enforces_deadline():
    release = Event()

    def blocking_tool():
        release.wait()

    harness = app.AgentHarness(
        tool_timeout=0.01,
        client=SimpleNamespace(),
    )

    try:
        with pytest.raises(TimeoutError, match="exceeded"):
            harness.invoke_tool(blocking_tool, {})
    finally:
        release.set()


def test_tool_timeout_becomes_a_failed_run():
    call = tool_call("search_flights", destination="Paris")

    def request_tool(**_kwargs):
        message = SimpleNamespace(tool_calls=[call], content="")
        return SimpleNamespace(message=message)

    harness = app.AgentHarness(client=SimpleNamespace(chat=request_tool))

    def exceed_deadline(_function, _arguments):
        raise TimeoutError("Tool execution exceeded its deadline")

    harness.invoke_tool = exceed_deadline
    state = harness.run("Find a flight")

    assert state.termination_reason == "tool_timeout"
    assert app.event_path(state) == [
        "run_started",
        "model_requested",
        "tool_requested:search_flights",
        "tool_failed:search_flights",
        "run_stopped",
    ]


def test_load_scenarios_rejects_invalid_field_types(tmp_path):
    path = tmp_path / "invalid-scenarios.json"
    path.write_text(
        """[
          {
            "name": "invalid purchase count",
            "task": "Find a flight",
            "approval": null,
            "expected_trajectory": ["run_started"],
            "forbidden_events": [],
            "expected_termination": "completed",
            "expected_purchase_count": "zero"
          }
        ]""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="expected_purchase_count"):
        app.load_scenarios(path)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"name": "not an array"}, "JSON array"),
        (
            [
                {
                    "name": "invalid trajectory",
                    "task": "Find a flight",
                    "approval": None,
                    "expected_trajectory": [1],
                    "forbidden_events": [],
                    "expected_termination": "completed",
                    "expected_purchase_count": 0,
                }
            ],
            "must contain strings",
        ),
        (
            [
                {
                    "name": "invalid approval",
                    "task": "Purchase a flight",
                    "approval": {"tool": "purchase_flight"},
                    "expected_trajectory": ["run_started"],
                    "forbidden_events": [],
                    "expected_termination": "completed",
                    "expected_purchase_count": 1,
                }
            ],
            "approval requires",
        ),
    ],
)
def test_load_scenarios_rejects_malformed_contracts(
    tmp_path,
    payload,
    message,
):
    path = tmp_path / "malformed-scenarios.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        app.load_scenarios(path)


def test_empty_scenario_suite_blocks_release():
    assert app.release_allowed([]) is False
