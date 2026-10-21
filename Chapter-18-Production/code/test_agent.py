from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import time
import threading

import pytest

from agent import (
    ApprovalAuthority,
    CancelledError,
    CancellationToken,
    Deadline,
    DeploymentInfo,
    DurableStore,
    Identity,
    InMemoryEventSink,
    ProductionAgent,
    RunContext,
    RunState,
    StaleActionClaim,
    ToolSpec,
    TravelTools,
    action_fingerprint,
    purchase_flight,
    search_flights,
)
from monitoring import should_alert, summarize_events


class FakeMessage:
    def __init__(self, content: str = "", tool_calls: list[Any] | None = None):
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls or []

    def model_dump(self, exclude_none: bool = True) -> dict[str, Any]:
        value = {"role": self.role, "content": self.content}
        if self.tool_calls:
            value["tool_calls"] = [
                {
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    }
                }
                for call in self.tool_calls
            ]
        return value


class FakeResponse:
    def __init__(self, message: FakeMessage):
        self.message = message


class FakeClient:
    def __init__(self, messages: list[FakeMessage]):
        self.responses = [FakeResponse(message) for message in messages]
        self.calls: list[dict[str, Any]] = []

    def chat(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(deepcopy(kwargs))
        return self.responses.pop(0)


def tool_call(name: str, **arguments: Any) -> Any:
    return SimpleNamespace(
        function=SimpleNamespace(name=name, arguments=arguments)
    )


@pytest.fixture
def deployment() -> DeploymentInfo:
    return DeploymentInfo(
        agent_version="travel-agent-test",
        source_revision="test-revision",
        model="fake-model",
        prompt_version="prompt-test",
        policy_version="policy-test",
        tool_schema_version="tools-test",
        evaluation_dataset="dataset-test",
        environment="test",
    )


@pytest.fixture
def identity() -> Identity:
    return Identity(
        subject="user-1842",
        tenant="travel",
        roles=frozenset({"traveler"}),
    )


def build_test_agent(tmp_path, deployment, messages):
    travel_tools = TravelTools()
    authority = ApprovalAuthority("test-secret")
    sink = InMemoryEventSink()
    tools = {
        "search_flights": ToolSpec(
            name="search_flights",
            schema=search_flights,
            handler=travel_tools.search_flights,
        ),
        "purchase_flight": ToolSpec(
            name="purchase_flight",
            schema=purchase_flight,
            handler=travel_tools.purchase_flight,
            reconcile=travel_tools.check_purchase,
            requires_approval=True,
            side_effecting=True,
        ),
    }
    agent = ProductionAgent(
        deployment=deployment,
        tools=tools,
        store=DurableStore(tmp_path / "agent.db"),
        approval_authority=authority,
        event_sink=sink,
        client=FakeClient(messages),
    )
    return agent, travel_tools, authority, sink


def context(identity, deployment, approval=None, cancellation=None):
    return RunContext(
        identity=identity,
        deployment=deployment,
        deadline=Deadline.after(30.0),
        cancellation=cancellation or CancellationToken(),
        approval=approval,
    )


def event_types(state) -> list[str]:
    return [event["event_type"] for event in state.events]


def test_unapproved_purchase_is_denied(
    tmp_path,
    deployment,
    identity,
):
    agent, tools, _, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(tool_calls=[tool_call("purchase_flight", flight_id="FL-204")])],
    )

    state = agent.run("Purchase FL-204", context(identity, deployment))

    assert state.termination_reason == "policy_denied"
    assert tools.purchases == []
    assert event_types(state) == [
        "run_started",
        "model_requested",
        "tool_requested",
        "policy_denied",
        "run_stopped",
    ]


def test_signed_approval_executes_once_and_replays(
    tmp_path,
    deployment,
    identity,
):
    calls = [
        FakeMessage(tool_calls=[tool_call("purchase_flight", flight_id="FL-204")]),
        FakeMessage(content="Purchased FL-204"),
        FakeMessage(tool_calls=[tool_call("purchase_flight", flight_id="FL-204")]),
        FakeMessage(content="Purchased FL-204"),
    ]
    agent, tools, authority, _ = build_test_agent(tmp_path, deployment, calls)
    approval = authority.issue(
        identity,
        "purchase_flight",
        {"flight_id": "FL-204"},
        "purchase-FL-204-user-1842",
    )
    run_context = context(identity, deployment, approval)

    first = agent.run("Purchase FL-204", run_context)
    second = agent.run("Purchase FL-204", run_context)

    assert first.termination_reason == "completed"
    assert second.termination_reason == "completed"
    assert tools.purchases == ["FL-204"]
    completed = [
        event
        for event in second.events
        if event["event_type"] == "tool_completed"
    ]
    assert completed[0]["replayed"] is True


def test_tampered_approval_is_rejected(
    tmp_path,
    deployment,
    identity,
):
    agent, tools, authority, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(tool_calls=[tool_call("purchase_flight", flight_id="FL-999")])],
    )
    approval = authority.issue(
        identity,
        "purchase_flight",
        {"flight_id": "FL-204"},
        "purchase-FL-204-user-1842",
    )
    tampered = replace(approval, arguments={"flight_id": "FL-999"})

    state = agent.run(
        "Purchase FL-999",
        context(identity, deployment, tampered),
    )

    assert state.termination_reason == "policy_denied"
    assert tools.purchases == []


def test_tool_role_is_enforced(tmp_path, deployment):
    identity = Identity(
        subject="auditor-1",
        tenant="travel",
        roles=frozenset({"auditor"}),
    )
    agent, _, _, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(tool_calls=[tool_call("search_flights", destination="Paris")])],
    )

    state = agent.run("Find a flight", context(identity, deployment))

    assert state.termination_reason == "policy_denied"


def test_tool_requires_signed_in_user(tmp_path, deployment):
    identity = Identity(
        subject="",
        tenant="travel",
        roles=frozenset({"traveler"}),
    )
    agent, _, _, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(tool_calls=[tool_call("search_flights", destination="Paris")])],
    )

    state = agent.run("Find flights", context(identity, deployment), "run-anonymous")

    assert state.termination_reason == "policy_denied"


def test_cancelled_run_stops_before_model_call(
    tmp_path,
    deployment,
    identity,
):
    agent, _, _, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(content="unused")],
    )
    cancellation = CancellationToken()
    cancellation.cancel()

    state = agent.run(
        "Find a flight",
        context(identity, deployment, cancellation=cancellation),
    )

    assert state.termination_reason == "cancelled"
    assert agent.client.calls == []


def test_checkpoint_contains_terminal_state(
    tmp_path,
    deployment,
    identity,
):
    agent, _, _, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(content="No tools needed")],
    )

    state = agent.run("Say hello", context(identity, deployment))
    restored = agent.store.load_checkpoint(state.run_id)

    assert restored is not None
    assert restored.termination_reason == "completed"
    assert restored.final_answer == "No tools needed"


def test_run_resumes_from_checkpoint(
    tmp_path,
    deployment,
    identity,
):
    agent, _, _, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(content="Resumed answer")],
    )
    interrupted = RunState(
        run_id="run-resume",
        messages=[
            {"role": "system", "content": "Use travel tools."},
            {"role": "user", "content": "Find a flight"},
            {"role": "tool", "tool_name": "search_flights", "content": "FL-204"},
        ],
        subject=identity.subject,
        tenant=identity.tenant,
        step=1,
    )
    agent.store.save_checkpoint(interrupted)

    state = agent.run(
        "This task is ignored during resume",
        context(identity, deployment),
        run_id="run-resume",
    )

    assert state.final_answer == "Resumed answer"
    assert state.step == 2
    assert event_types(state)[0] == "run_resumed"
    assert agent.client.calls[0]["messages"][2]["content"] == "FL-204"


def test_run_resumes_pending_tool_before_model(
    tmp_path,
    deployment,
    identity,
):
    agent, _, _, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(content="Flight found")],
    )
    interrupted = RunState(
        run_id="run-pending-tool",
        messages=[
            {"role": "system", "content": "Use travel tools."},
            {"role": "user", "content": "Find a flight to Paris"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "search_flights",
                            "arguments": {"destination": "Paris"},
                        }
                    }
                ],
            },
        ],
        subject=identity.subject,
        tenant=identity.tenant,
        step=1,
        pending_tool_calls=[
            {
                "name": "search_flights",
                "arguments": {"destination": "Paris"},
                "status": "requested",
            }
        ],
    )
    agent.store.save_checkpoint(interrupted)

    state = agent.run(
        "ignored",
        context(identity, deployment),
        run_id="run-pending-tool",
    )

    assert state.final_answer == "Flight found"
    assert state.pending_tool_calls == []
    assert event_types(state).count("tool_requested") == 0
    assert event_types(state).count("tool_completed") == 1
    assert agent.client.calls[0]["messages"][-1]["role"] == "tool"


def test_reconciled_run_resumes_to_completion(
    tmp_path,
    deployment,
    identity,
):
    agent, tools, authority, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(content="Purchase confirmed")],
    )
    approval = authority.issue(
        identity,
        "purchase_flight",
        {"flight_id": "FL-204"},
        "purchase-key",
    )
    fingerprint = action_fingerprint("purchase_flight", {"flight_id": "FL-204"})
    claim = agent.store.claim_action(
        identity.tenant,
        identity.subject,
        "purchase-key",
        fingerprint,
        owner=identity.subject,
    )
    agent.store.mark_status_unknown(
        identity.tenant,
        identity.subject,
        "purchase-key",
        claim.generation,
    )
    interrupted = RunState(
        run_id="run-reconcile",
        messages=[
            {"role": "system", "content": "Use travel tools."},
            {"role": "user", "content": "Purchase FL-204"},
        ],
        subject=identity.subject,
        tenant=identity.tenant,
        step=1,
        pending_tool_calls=[
            {
                "name": "purchase_flight",
                "arguments": {"flight_id": "FL-204"},
                "status": "requested",
            }
        ],
        termination_reason="awaiting_reconciliation",
    )
    agent.store.save_checkpoint(interrupted)
    tools.provider_results[(identity.tenant, identity.subject, "purchase-key")] = (
        "Purchased FL-204"
    )
    evidence = agent.reconcile_action(
        "purchase_flight",
        {"flight_id": "FL-204"},
        context(identity, deployment, approval),
    )
    assert evidence.committed is True

    state = agent.run(
        "ignored",
        context(identity, deployment, approval),
        run_id="run-reconcile",
    )

    assert state.termination_reason == "completed"
    assert state.final_answer == "Purchase confirmed"
    assert tools.purchases == []
    completed = [event for event in state.events if event["event_type"] == "tool_completed"]
    assert completed[0]["replayed"] is True


def test_agent_reconciliation_can_mark_action_retryable(
    tmp_path,
    deployment,
    identity,
):
    agent, _, authority, _ = build_test_agent(tmp_path, deployment, [])
    arguments = {"flight_id": "FL-204"}
    approval = authority.issue(
        identity,
        "purchase_flight",
        arguments,
        "not-committed-key",
    )
    claim = agent.store.claim_action(
        identity.tenant,
        identity.subject,
        approval.idempotency_key,
        action_fingerprint("purchase_flight", arguments),
        owner=identity.subject,
    )
    agent.store.mark_status_unknown(
        identity.tenant,
        identity.subject,
        approval.idempotency_key,
        claim.generation,
    )

    evidence = agent.reconcile_action(
        "purchase_flight",
        arguments,
        context(identity, deployment, approval),
    )
    retry = agent.store.claim_action(
        identity.tenant,
        identity.subject,
        approval.idempotency_key,
        action_fingerprint("purchase_flight", arguments),
        owner="worker-2",
    )

    assert evidence.committed is False
    assert retry.execute is True


def test_active_action_pauses_run_for_later_resume(
    tmp_path,
    deployment,
    identity,
):
    agent, _, authority, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(tool_calls=[tool_call("purchase_flight", flight_id="FL-204")])],
    )
    arguments = {"flight_id": "FL-204"}
    approval = authority.issue(
        identity,
        "purchase_flight",
        arguments,
        "active-key",
    )
    agent.store.claim_action(
        identity.tenant,
        identity.subject,
        approval.idempotency_key,
        action_fingerprint("purchase_flight", arguments),
        owner="worker-1",
    )

    state = agent.run(
        "Purchase FL-204",
        context(identity, deployment, approval),
    )

    assert state.termination_reason == "awaiting_reconciliation"
    assert state.pending_tool_calls[0]["status"] == "requested"
    assert state.events[-1]["reason"] == "tool_in_progress"


def test_missing_approval_uses_stable_reason_code(
    tmp_path,
    deployment,
    identity,
):
    agent, _, _, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(tool_calls=[tool_call("purchase_flight", flight_id="FL-204")])],
    )

    state = agent.run("Purchase FL-204", context(identity, deployment))
    denied = next(
        event for event in state.events if event["event_type"] == "policy_denied"
    )

    assert denied["reason_code"] == "approval_required"


def test_side_effect_timeout_reconciles_and_resumes_end_to_end(
    tmp_path,
    deployment,
    identity,
):
    agent, tools, authority, _ = build_test_agent(
        tmp_path,
        deployment,
        [
            FakeMessage(
                tool_calls=[tool_call("purchase_flight", flight_id="FL-204")]
            ),
            FakeMessage(content="Purchase confirmed"),
        ],
    )
    original_spec = agent.tools["purchase_flight"]
    handler_calls = 0

    def slow_purchase(arguments, run_context):
        nonlocal handler_calls
        handler_calls += 1
        time.sleep(0.1)
        return tools.purchase_flight(arguments, run_context)

    agent.tools["purchase_flight"] = replace(
        original_spec,
        handler=slow_purchase,
        timeout_seconds=0.01,
    )
    approval = authority.issue(
        identity,
        "purchase_flight",
        {"flight_id": "FL-204"},
        "timeout-purchase-key",
    )
    run_context = context(identity, deployment, approval)

    paused = agent.run("Purchase FL-204", run_context)

    assert paused.termination_reason == "awaiting_reconciliation"
    assert paused.pending_tool_calls[0]["status"] == "requested"
    fingerprint = action_fingerprint("purchase_flight", {"flight_id": "FL-204"})
    agent.store.reconcile_action(
        identity.tenant,
        identity.subject,
        "timeout-purchase-key",
        fingerprint,
        committed=True,
        provider_result="Purchased FL-204",
    )

    resumed = agent.run(
        "ignored",
        context(identity, deployment, approval),
        run_id=paused.run_id,
    )

    assert resumed.termination_reason == "completed"
    assert resumed.final_answer == "Purchase confirmed"
    completed = [
        event for event in resumed.events if event["event_type"] == "tool_completed"
    ]
    assert completed[0]["replayed"] is True
    assert handler_calls == 1


@pytest.mark.parametrize(
    "provider_error",
    [OSError("provider disconnected"), PermissionError("provider rejected request")],
)
def test_provider_failure_pauses_for_reconciliation(
    tmp_path,
    deployment,
    identity,
    provider_error,
):
    agent, _, authority, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(tool_calls=[tool_call("purchase_flight", flight_id="FL-204")])],
    )
    original_spec = agent.tools["purchase_flight"]
    agent.tools["purchase_flight"] = replace(
        original_spec,
        handler=lambda arguments, run_context: (_ for _ in ()).throw(
            provider_error
        ),
    )
    approval = authority.issue(
        identity,
        "purchase_flight",
        {"flight_id": "FL-204"},
        "provider-failure-key",
    )

    state = agent.run("Purchase FL-204", context(identity, deployment, approval))

    assert state.termination_reason == "awaiting_reconciliation"
    assert state.pending_tool_calls[0]["status"] == "requested"
    row = agent.store.connection.execute(
        "SELECT status FROM actions WHERE idempotency_key=?",
        ("provider-failure-key",),
    ).fetchone()
    assert row["status"] == "status_unknown"


def test_expired_approval_can_replay_completed_action(
    tmp_path,
    deployment,
    identity,
):
    agent, tools, authority, _ = build_test_agent(tmp_path, deployment, [])
    arguments = {"flight_id": "FL-204"}
    approval = authority.issue(
        identity,
        "purchase_flight",
        arguments,
        "completed-key",
        lifetime=timedelta(seconds=-1),
    )
    fingerprint = action_fingerprint("purchase_flight", arguments)
    claim = agent.store.claim_action(
        identity.tenant,
        identity.subject,
        approval.idempotency_key,
        fingerprint,
        owner=identity.subject,
    )
    agent.store.complete_action(
        identity.tenant,
        identity.subject,
        approval.idempotency_key,
        claim.generation,
        "Purchased FL-204",
    )

    result, replayed = agent.execute_tool(
        "purchase_flight",
        arguments,
        context(identity, deployment, approval),
    )

    assert result == "Purchased FL-204"
    assert replayed is True
    assert tools.purchases == []


@pytest.mark.parametrize("expires_at", ["not-a-timestamp", "2026-08-01T12:00:00"])
def test_invalid_approval_expiry_is_policy_denied(
    tmp_path,
    deployment,
    identity,
    expires_at,
):
    agent, tools, authority, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(tool_calls=[tool_call("purchase_flight", flight_id="FL-204")])],
    )
    approval = authority.issue(
        identity,
        "purchase_flight",
        {"flight_id": "FL-204"},
        "invalid-expiry-key",
    )
    approval = replace(approval, expires_at=expires_at)

    state = agent.run("Purchase FL-204", context(identity, deployment, approval))

    assert state.termination_reason == "policy_denied"
    assert tools.purchases == []


def test_regression_scenarios_execute_in_deterministic_harness(
    tmp_path,
    deployment,
    identity,
):
    scenario_path = Path(__file__).with_name("regression-scenarios.json")
    scenarios = json.loads(scenario_path.read_text(encoding="utf-8"))

    for scenario in scenarios:
        agent, _, _, _ = build_test_agent(
            tmp_path,
            deployment,
            [FakeMessage(content="Which state do you mean?")],
        )
        state = agent.run(scenario["task"], context(identity, deployment))
        trajectory = event_types(state)

        expected_index = 0
        for event_type in trajectory:
            if event_type == scenario["expected_trajectory"][expected_index]:
                expected_index += 1
                if expected_index == len(scenario["expected_trajectory"]):
                    break
        assert expected_index == len(scenario["expected_trajectory"])
        for forbidden in scenario.get("forbidden_events", []):
            event_type, _, tool = forbidden.partition(":")
            assert not any(
                event["event_type"] == event_type
                and (not tool or event.get("tool") == tool)
                for event in state.events
            )
        assert state.termination_reason == scenario["expected_termination"]


def test_run_resume_rejects_another_identity(
    tmp_path,
    deployment,
    identity,
):
    agent, _, _, _ = build_test_agent(tmp_path, deployment, [])
    state = RunState(
        run_id="private-run",
        messages=[],
        subject=identity.subject,
        tenant=identity.tenant,
        termination_reason="completed",
    )
    agent.store.save_checkpoint(state)
    intruder = Identity(
        subject="user-9999",
        tenant=identity.tenant,
        roles=identity.roles,
    )

    with pytest.raises(PermissionError, match="another identity"):
        agent.run("ignored", context(intruder, deployment), run_id=state.run_id)


def test_model_call_observes_remaining_deadline(
    tmp_path,
    deployment,
    identity,
):
    class SlowClient:
        def chat(self, **kwargs):
            time.sleep(0.2)
            return FakeResponse(FakeMessage(content="Too late"))

    agent, _, _, _ = build_test_agent(tmp_path, deployment, [])
    agent.client = SlowClient()
    run_context = RunContext(
        identity=identity,
        deployment=deployment,
        deadline=Deadline.after(0.02),
        cancellation=CancellationToken(),
    )

    state = agent.run("Find a flight", run_context)

    assert state.termination_reason == "model_timeout"


def test_cancellation_is_observed_while_waiting_for_model(
    tmp_path,
    deployment,
    identity,
):
    class SlowClient:
        def chat(self, **kwargs):
            time.sleep(0.2)
            return FakeResponse(FakeMessage(content="Too late"))

    agent, _, _, _ = build_test_agent(tmp_path, deployment, [])
    agent.client = SlowClient()
    cancellation = CancellationToken()
    timer = threading.Timer(0.02, cancellation.cancel)
    timer.start()

    state = agent.run(
        "Find a flight",
        context(identity, deployment, cancellation=cancellation),
    )
    timer.cancel()

    assert state.termination_reason == "cancelled"


def test_cancellation_is_observed_while_waiting_for_tool(
    tmp_path,
    deployment,
    identity,
):
    agent, _, _, _ = build_test_agent(tmp_path, deployment, [])
    slow_tool = ToolSpec(
        name="slow_tool",
        schema=search_flights,
        handler=lambda arguments, run_context: time.sleep(0.2),
        timeout_seconds=1.0,
    )
    cancellation = CancellationToken()
    timer = threading.Timer(0.02, cancellation.cancel)
    timer.start()

    with pytest.raises(CancelledError, match="cancelled"):
        agent.invoke_tool(
            slow_tool,
            {},
            context(identity, deployment, cancellation=cancellation),
        )
    timer.cancel()


def test_unknown_action_can_be_reconciled(tmp_path):
    store = DurableStore(tmp_path / "agent.db")
    fingerprint = action_fingerprint("purchase_flight", {"flight_id": "FL-204"})
    claim = store.claim_action(
        "travel", "user-1", "purchase-key", fingerprint, owner="worker-1"
    )
    store.mark_status_unknown(
        "travel", "user-1", "purchase-key", claim.generation
    )

    store.reconcile_action(
        "travel",
        "user-1",
        "purchase-key",
        fingerprint,
        committed=True,
        provider_result="Purchased FL-204",
    )
    claim = store.claim_action(
        "travel", "user-1", "purchase-key", fingerprint, owner="worker-2"
    )

    assert claim.execute is False
    assert claim.result == "Purchased FL-204"


def test_expired_action_lease_requires_reconciliation(tmp_path):
    store = DurableStore(tmp_path / "agent.db")
    fingerprint = action_fingerprint("purchase_flight", {"flight_id": "FL-204"})
    store.claim_action(
        "travel",
        "user-1",
        "purchase-key",
        fingerprint,
        owner="worker-1",
        lease_seconds=-1,
    )

    with pytest.raises(Exception, match="reconcile"):
        store.claim_action(
            "travel", "user-1", "purchase-key", fingerprint, owner="worker-2"
        )

    store.reconcile_action(
        "travel",
        "user-1",
        "purchase-key",
        fingerprint,
        committed=True,
        provider_result="Purchased FL-204",
    )
    replay = store.claim_action(
        "travel", "user-1", "purchase-key", fingerprint, owner="worker-2"
    )
    assert replay.execute is False


def test_reconciliation_can_confirm_action_did_not_commit(tmp_path):
    store = DurableStore(tmp_path / "agent.db")
    fingerprint = action_fingerprint("purchase_flight", {"flight_id": "FL-204"})
    claim = store.claim_action(
        "travel", "user-1", "purchase-key", fingerprint, owner="worker-1"
    )
    store.mark_status_unknown(
        "travel", "user-1", "purchase-key", claim.generation
    )

    store.reconcile_action(
        "travel", "user-1", "purchase-key", fingerprint, committed=False
    )
    retry = store.claim_action(
        "travel", "user-1", "purchase-key", fingerprint, owner="worker-2"
    )

    assert retry.execute is True


def test_reconciliation_rejects_active_action(tmp_path):
    store = DurableStore(tmp_path / "agent.db")
    fingerprint = action_fingerprint("purchase_flight", {"flight_id": "FL-204"})
    store.claim_action(
        "travel", "user-1", "purchase-key", fingerprint, owner="worker-1"
    )

    with pytest.raises(ValueError, match="unknown status"):
        store.reconcile_action(
            "travel",
            "user-1",
            "purchase-key",
            fingerprint,
            committed=True,
            provider_result="Purchased FL-204",
        )


def test_events_include_versions_without_raw_arguments(
    tmp_path,
    deployment,
    identity,
):
    agent, _, _, sink = build_test_agent(
        tmp_path,
        deployment,
        [
            FakeMessage(
                tool_calls=[tool_call("search_flights", destination="Paris")]
            ),
            FakeMessage(content="FL-204 is available"),
        ],
    )

    agent.run("Find a flight", context(identity, deployment))
    request = next(
        event for event in sink.events if event["event_type"] == "tool_requested"
    )

    assert request["agent_version"] == "travel-agent-test"
    assert request["model_version"] == "fake-model"
    assert request["policy_version"] == "policy-test"
    assert "arguments_hash" in request
    assert "arguments" not in request


def test_event_outbox_survives_sink_failure(
    tmp_path,
    deployment,
    identity,
):
    class FailingSink:
        def emit(self, event):
            raise OSError("telemetry unavailable")

    agent, _, _, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(content="Completed despite telemetry outage")],
    )
    agent.event_sink = FailingSink()

    state = agent.run("Say hello", context(identity, deployment))

    assert state.termination_reason == "completed"
    restored = agent.store.load_checkpoint(state.run_id)
    assert restored is not None
    assert restored.final_answer == "Completed despite telemetry outage"
    assert len(agent.store.load_pending_events()) == 3

    recovered_sink = InMemoryEventSink()
    agent.event_sink = recovered_sink
    agent.publish_pending_events()

    assert [event["event_type"] for event in recovered_sink.events] == [
        "run_started",
        "model_requested",
        "run_completed",
    ]
    assert agent.store.load_pending_events() == []


def test_idempotency_key_cannot_change_action(tmp_path):
    store = DurableStore(tmp_path / "agent.db")
    first = action_fingerprint("purchase_flight", {"flight_id": "FL-204"})
    second = action_fingerprint("purchase_flight", {"flight_id": "FL-999"})
    store.claim_action(
        "travel", "user-1", "purchase-key", first, owner="worker-1"
    )

    with pytest.raises(ValueError, match="another action"):
        store.claim_action(
            "travel", "user-1", "purchase-key", second, owner="worker-2"
        )


def test_approval_rejects_python_equal_argument_types(deployment, identity):
    authority = ApprovalAuthority("test-secret")
    approval = authority.issue(
        identity,
        "purchase_flight",
        {"flight_id": 1},
        "purchase-key",
    )

    with pytest.raises(PermissionError, match="does not match"):
        authority.verify(
            approval,
            identity,
            "purchase_flight",
            {"flight_id": True},
        )


def test_idempotency_keys_are_scoped_by_tenant_and_subject(tmp_path):
    store = DurableStore(tmp_path / "agent.db")
    fingerprint = action_fingerprint("purchase_flight", {"flight_id": "FL-204"})

    first = store.claim_action(
        "tenant-a", "user-1", "purchase-key", fingerprint, owner="worker-a"
    )
    second = store.claim_action(
        "tenant-b", "user-1", "purchase-key", fingerprint, owner="worker-b"
    )

    assert first.execute is True
    assert second.execute is True


def test_stale_worker_cannot_complete_reconciled_action(tmp_path):
    store = DurableStore(tmp_path / "agent.db")
    fingerprint = action_fingerprint("purchase_flight", {"flight_id": "FL-204"})
    stale = store.claim_action(
        "travel", "user-1", "purchase-key", fingerprint, owner="worker-1"
    )
    store.mark_status_unknown(
        "travel", "user-1", "purchase-key", stale.generation
    )
    store.reconcile_action(
        "travel", "user-1", "purchase-key", fingerprint, committed=False
    )
    current = store.claim_action(
        "travel", "user-1", "purchase-key", fingerprint, owner="worker-2"
    )

    with pytest.raises(StaleActionClaim):
        store.complete_action(
            "travel",
            "user-1",
            "purchase-key",
            stale.generation,
            "stale result",
        )
    store.complete_action(
        "travel",
        "user-1",
        "purchase-key",
        current.generation,
        "current result",
    )


def test_monitoring_summarizes_rates():
    events = [
        {"event_type": "run_started", "run_id": "run-1"},
        {"event_type": "policy_denied", "run_id": "run-1"},
        {
            "event_type": "run_stopped",
            "run_id": "run-1",
            "reason": "policy_denied",
        },
        {"event_type": "run_started", "run_id": "run-2"},
        {"event_type": "run_completed", "run_id": "run-2"},
    ]

    summary = summarize_events(events)

    assert summary["runs"] == 2
    assert summary["policy_denied_rate"] == 0.5
    assert summary["termination_counts"] == {
        "completed": 1,
        "policy_denied": 1,
    }


def test_monitoring_counts_denied_runs_not_denial_events():
    events = [
        {"event_type": "run_started", "run_id": "run-1"},
        {"event_type": "policy_denied", "run_id": "run-1"},
        {"event_type": "policy_denied", "run_id": "run-1"},
        {"event_type": "run_stopped", "run_id": "run-1", "reason": "policy_denied"},
    ]

    assert summarize_events(events)["policy_denied_rate"] == 1.0


def test_monitoring_deduplicates_terminal_events_and_counts_paused_timeout():
    events = [
        {"event_type": "run_started", "run_id": "run-1"},
        {"event_type": "run_stopped", "run_id": "run-1", "reason": "tool_error"},
        {"event_type": "run_stopped", "run_id": "run-1", "reason": "tool_error"},
        {"event_type": "run_started", "run_id": "run-2"},
        {
            "event_type": "run_paused",
            "run_id": "run-2",
            "reason": "tool_timeout",
            "tool": "purchase_flight",
        },
    ]

    summary = summarize_events(events)

    assert summary["termination_counts"] == {"tool_error": 1, "tool_timeout": 1}
    assert summary["tool_timeout_rate"] == 0.5


def test_monitoring_tool_filter_uses_causal_terminal_tool():
    events = [
        {"event_type": "run_started", "run_id": "run-1"},
        {"event_type": "tool_requested", "run_id": "run-1", "tool": "search_flights"},
        {"event_type": "tool_completed", "run_id": "run-1", "tool": "search_flights"},
        {"event_type": "tool_requested", "run_id": "run-1", "tool": "purchase_flight"},
        {
            "event_type": "run_paused",
            "run_id": "run-1",
            "reason": "tool_timeout",
            "tool": "purchase_flight",
        },
    ]

    summary = summarize_events(events, tool="search_flights")

    assert summary["runs"] == 0
    assert summary["incomplete_runs"] == 1
    assert summary["tool_timeout_rate"] == 0.0


def test_monitoring_tool_filter_uses_causal_denial_tool():
    events = [
        {"event_type": "run_started", "run_id": "run-1"},
        {"event_type": "tool_requested", "run_id": "run-1", "tool": "search_flights"},
        {
            "event_type": "policy_denied",
            "run_id": "run-1",
            "tool": "purchase_flight",
        },
        {
            "event_type": "run_stopped",
            "run_id": "run-1",
            "reason": "policy_denied",
            "tool": "purchase_flight",
        },
    ]

    summary = summarize_events(events, tool="search_flights")

    assert summary["runs"] == 0
    assert summary["incomplete_runs"] == 1
    assert summary["policy_denied_rate"] == 0.0


def test_monitoring_excludes_incomplete_runs_from_rate_denominator():
    events = [
        {"event_type": "run_started", "run_id": "completed"},
        {"event_type": "run_completed", "run_id": "completed"},
        {"event_type": "run_started", "run_id": "incomplete"},
    ]

    summary = summarize_events(events)

    assert summary["runs"] == 1
    assert summary["incomplete_runs"] == 1
    assert summary["policy_denied_rate"] == 0.0


def test_monitoring_filters_by_window_and_tool():
    now = datetime.now(timezone.utc)
    recent = now.isoformat()
    old = (now - timedelta(hours=1)).isoformat()
    events = [
        {"event_type": "run_started", "run_id": "purchase", "timestamp": recent},
        {
            "event_type": "policy_denied",
            "run_id": "purchase",
            "tool": "purchase_flight",
            "timestamp": recent,
        },
        {"event_type": "run_started", "run_id": "search", "timestamp": recent},
        {
            "event_type": "tool_requested",
            "run_id": "search",
            "tool": "search_flights",
            "timestamp": recent,
        },
        {"event_type": "run_started", "run_id": "old", "timestamp": old},
        {
            "event_type": "policy_denied",
            "run_id": "old",
            "tool": "purchase_flight",
            "timestamp": old,
        },
    ]

    summary = summarize_events(
        events,
        tool="purchase_flight",
        since=now - timedelta(minutes=15),
        until=now + timedelta(seconds=1),
    )

    assert summary["runs"] == 1
    assert summary["policy_denied_rate"] == 1.0


def test_monitoring_counts_run_started_before_window():
    now = datetime.now(timezone.utc)
    events = [
        {
            "event_type": "run_started",
            "run_id": "run-1",
            "timestamp": (now - timedelta(minutes=16)).isoformat(),
        },
        {
            "event_type": "policy_denied",
            "run_id": "run-1",
            "tool": "purchase_flight",
            "timestamp": now.isoformat(),
        },
    ]

    summary = summarize_events(
        events,
        tool="purchase_flight",
        since=now - timedelta(minutes=15),
    )

    assert summary["runs"] == 1
    assert summary["policy_denied_rate"] == 1.0


def test_alert_requires_volume_threshold_and_baseline_change():
    assert should_alert(0.08, 0.02, 200, 0.05, 100) is True
    assert should_alert(0.08, 0.02, 20, 0.05, 100) is False
    assert should_alert(0.04, 0.01, 200, 0.05, 100) is False


def test_expired_approval_is_rejected(
    tmp_path,
    deployment,
    identity,
):
    agent, tools, authority, _ = build_test_agent(
        tmp_path,
        deployment,
        [FakeMessage(tool_calls=[tool_call("purchase_flight", flight_id="FL-204")])],
    )
    approval = authority.issue(
        identity,
        "purchase_flight",
        {"flight_id": "FL-204"},
        "expired-key",
        lifetime=timedelta(seconds=-1),
    )

    state = agent.run(
        "Purchase FL-204",
        context(identity, deployment, approval),
    )

    assert state.termination_reason == "policy_denied"
    assert tools.purchases == []
