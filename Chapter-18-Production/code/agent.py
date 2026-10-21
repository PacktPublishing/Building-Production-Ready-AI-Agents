from __future__ import annotations

import argparse
import hashlib
import hmac
import inspect
import json
import os
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Protocol, get_type_hints

from httpx import TimeoutException
from ollama import ChatResponse, Client, ResponseError


MODEL = "qwen2.5:1.5b"
MAX_STEPS = 4
MODEL_TIMEOUT_SECONDS = 30.0
TOOL_TIMEOUT_SECONDS = 5.0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def action_fingerprint(tool: str, arguments: dict[str, Any]) -> str:
    value = canonical_json({"tool": tool, "arguments": arguments})
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_tool_arguments(
    schema: Callable[..., Any],
    arguments: dict[str, Any],
) -> None:
    signature = inspect.signature(schema)
    hints = get_type_hints(schema)
    expected = set(signature.parameters)
    if set(arguments) != expected:
        raise ValueError("Tool arguments do not match the schema")
    for name, value in arguments.items():
        expected_type = hints.get(name)
        if expected_type is not None and type(value) is not expected_type:
            raise ValueError(f"Tool argument {name} has the wrong type")


@dataclass(frozen=True)
class DeploymentInfo:
    agent_version: str
    source_revision: str
    model: str
    prompt_version: str
    policy_version: str
    tool_schema_version: str
    evaluation_dataset: str
    environment: str

    @classmethod
    def load(cls, path: str | Path) -> DeploymentInfo:
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass(frozen=True)
class Identity:
    subject: str
    tenant: str
    roles: frozenset[str]


@dataclass(frozen=True)
class Approval:
    approval_id: str
    subject: str
    tenant: str
    tool: str
    arguments: dict[str, Any]
    idempotency_key: str
    expires_at: str
    signature: str

    def signed_fields(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "subject": self.subject,
            "tenant": self.tenant,
            "tool": self.tool,
            "arguments": self.arguments,
            "idempotency_key": self.idempotency_key,
            "expires_at": self.expires_at,
        }


class ApprovalAuthority:
    """Issues approvals for the local example and verifies them in the harness."""

    def __init__(self, secret: str):
        if not secret:
            raise ValueError("Approval signing secret is required")
        self._secret = secret.encode("utf-8")

    def _sign(self, fields: dict[str, Any]) -> str:
        return hmac.new(
            self._secret,
            canonical_json(fields).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def issue(
        self,
        identity: Identity,
        tool: str,
        arguments: dict[str, Any],
        idempotency_key: str,
        lifetime: timedelta = timedelta(minutes=5),
    ) -> Approval:
        fields = {
            "approval_id": f"approval-{uuid.uuid4().hex[:8]}",
            "subject": identity.subject,
            "tenant": identity.tenant,
            "tool": tool,
            "arguments": arguments,
            "idempotency_key": idempotency_key,
            "expires_at": (utc_now() + lifetime).isoformat(),
        }
        return Approval(**fields, signature=self._sign(fields))

    def verify_binding(
        self,
        approval: Approval | None,
        identity: Identity,
        tool: str,
        arguments: dict[str, Any],
    ) -> Approval:
        if approval is None:
            raise PermissionError("Approval required")
        if not hmac.compare_digest(
            approval.signature,
            self._sign(approval.signed_fields()),
        ):
            raise PermissionError("Approval signature is invalid")
        if approval.subject != identity.subject or approval.tenant != identity.tenant:
            raise PermissionError("Approval belongs to another identity")
        if approval.tool != tool or action_fingerprint(
            approval.tool,
            approval.arguments,
        ) != action_fingerprint(tool, arguments):
            raise PermissionError("Approval does not match the requested action")
        return approval

    def verify_expiry(self, approval: Approval) -> None:
        try:
            expires_at = datetime.fromisoformat(approval.expires_at)
        except (TypeError, ValueError) as error:
            raise PermissionError("Approval expiry is invalid") from error
        if expires_at.tzinfo is None:
            raise PermissionError("Approval expiry must include a timezone")
        if expires_at <= utc_now():
            raise PermissionError("Approval has expired")

    def verify(
        self,
        approval: Approval | None,
        identity: Identity,
        tool: str,
        arguments: dict[str, Any],
    ) -> Approval:
        approval = self.verify_binding(approval, identity, tool, arguments)
        self.verify_expiry(approval)
        return approval


class CancellationToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise CancelledError("Run was cancelled")


class CancelledError(RuntimeError):
    pass


@dataclass(frozen=True)
class Deadline:
    expires_at: float

    @classmethod
    def after(cls, seconds: float) -> Deadline:
        return cls(time.monotonic() + seconds)

    def remaining_seconds(self) -> float:
        remaining = self.expires_at - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Run deadline exceeded")
        return remaining


@dataclass
class RunState:
    run_id: str
    messages: list[dict[str, Any]]
    subject: str = ""
    tenant: str = ""
    step: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    pending_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    final_answer: str | None = None
    termination_reason: str | None = None


@dataclass(frozen=True)
class RunContext:
    identity: Identity
    deployment: DeploymentInfo
    deadline: Deadline
    cancellation: CancellationToken
    approval: Approval | None = None


ToolHandler = Callable[[dict[str, Any], RunContext], Any]
ReconciliationHandler = Callable[[str, RunContext], "ReconciliationResult"]


@dataclass(frozen=True)
class ReconciliationResult:
    committed: bool
    result: Any = None


@dataclass(frozen=True)
class AuthPolicy:
    logged_in: bool
    roles: frozenset[str]


def auth(*, logged_in: bool, roles: list[str]):
    policy = AuthPolicy(logged_in=logged_in, roles=frozenset(roles))

    def decorate(tool: Callable[..., Any]) -> Callable[..., Any]:
        setattr(tool, "auth_policy", policy)
        return tool

    return decorate


@dataclass(frozen=True)
class ToolSpec:
    name: str
    schema: Callable[..., Any]
    handler: ToolHandler
    reconcile: ReconciliationHandler | None = None
    requires_approval: bool = False
    side_effecting: bool = False
    timeout_seconds: float = TOOL_TIMEOUT_SECONDS

    @property
    def auth_policy(self) -> AuthPolicy:
        policy = getattr(self.schema, "auth_policy", None)
        if not isinstance(policy, AuthPolicy):
            raise ValueError(f"Tool {self.name!r} has no @auth policy")
        return policy

    @property
    def allowed_roles(self) -> frozenset[str]:
        return self.auth_policy.roles


class EventSink(Protocol):
    def emit(self, event: dict[str, Any]) -> None: ...


class JsonLinesEventSink:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: dict[str, Any]) -> None:
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")


class InMemoryEventSink:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def emit(self, event: dict[str, Any]) -> None:
        self.events.append(event.copy())


class ActionInProgress(RuntimeError):
    pass


class UnknownActionStatus(RuntimeError):
    pass


class SideEffectStatusUnknown(RuntimeError):
    pass


class StaleActionClaim(RuntimeError):
    pass


@dataclass(frozen=True)
class ActionClaim:
    execute: bool
    status: str
    idempotency_key: str
    result: Any = None
    generation: int | None = None


class DurableStore:
    """SQLite teaching adapter for checkpoints and atomic action claims."""

    def __init__(self, path: str | Path):
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    run_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS actions (
                    tenant TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    lease_expires_at REAL NOT NULL,
                    result_json TEXT,
                    PRIMARY KEY(tenant, subject, idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS event_outbox (
                    event_id TEXT PRIMARY KEY,
                    event_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    published_at TEXT
                );
                """
            )

    def save_checkpoint(self, state: RunState) -> None:
        payload = canonical_json(asdict(state))
        with self._lock, self.connection:
            self.connection.execute(
                """
                INSERT INTO checkpoints(run_id, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    state_json=excluded.state_json,
                    updated_at=excluded.updated_at
                """,
                (state.run_id, payload, utc_now().isoformat()),
            )

    def load_checkpoint(self, run_id: str) -> RunState | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT state_json FROM checkpoints WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return RunState(**json.loads(row["state_json"])) if row else None

    def save_event_checkpoint(
        self,
        state: RunState,
        event: dict[str, Any],
    ) -> None:
        payload = canonical_json(asdict(state))
        with self._lock, self.connection:
            self.connection.execute(
                """
                INSERT INTO checkpoints(run_id, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    state_json=excluded.state_json,
                    updated_at=excluded.updated_at
                """,
                (state.run_id, payload, utc_now().isoformat()),
            )
            self.connection.execute(
                """
                INSERT INTO event_outbox(
                    event_id, event_json, created_at, published_at
                ) VALUES (?, ?, ?, NULL)
                """,
                (
                    event["event_id"],
                    canonical_json(event),
                    event["timestamp"],
                ),
            )

    def load_pending_events(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT event_json FROM event_outbox
                WHERE published_at IS NULL
                ORDER BY created_at, rowid
                """
            ).fetchall()
        return [json.loads(row["event_json"]) for row in rows]

    def mark_event_published(self, event_id: str) -> None:
        with self._lock, self.connection:
            self.connection.execute(
                """
                UPDATE event_outbox SET published_at=? WHERE event_id=?
                """,
                (utc_now().isoformat(), event_id),
            )

    def claim_action(
        self,
        tenant: str,
        subject: str,
        idempotency_key: str,
        fingerprint: str,
        owner: str,
        lease_seconds: float = 30.0,
    ) -> ActionClaim:
        now = time.time()
        with self._lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                row = self.connection.execute(
                    """
                    SELECT * FROM actions
                    WHERE tenant=? AND subject=? AND idempotency_key=?
                    """,
                    (tenant, subject, idempotency_key),
                ).fetchone()
                if row is None:
                    self.connection.execute(
                        """
                        INSERT INTO actions(
                            tenant, subject, idempotency_key, fingerprint,
                            status, owner, generation, lease_expires_at, result_json
                        ) VALUES (?, ?, ?, ?, 'started', ?, 1, ?, NULL)
                        """,
                        (
                            tenant,
                            subject,
                            idempotency_key,
                            fingerprint,
                            owner,
                            now + lease_seconds,
                        ),
                    )
                    self.connection.commit()
                    return ActionClaim(
                        execute=True,
                        status="started",
                        idempotency_key=idempotency_key,
                        generation=1,
                    )
                if row["fingerprint"] != fingerprint:
                    raise ValueError("Idempotency key belongs to another action")
                if row["status"] == "completed":
                    self.connection.commit()
                    return ActionClaim(
                        execute=False,
                        status="completed",
                        idempotency_key=idempotency_key,
                        result=json.loads(row["result_json"]),
                        generation=row["generation"],
                    )
                if row["status"] == "status_unknown":
                    raise UnknownActionStatus(
                        "Reconcile the external action before retrying"
                    )
                if row["status"] == "started" and row["lease_expires_at"] > now:
                    raise ActionInProgress("Another worker owns the action lease")
                if row["status"] == "retryable":
                    generation = row["generation"] + 1
                    self.connection.execute(
                        """
                        UPDATE actions
                        SET status='started', owner=?, generation=?,
                            lease_expires_at=?, result_json=NULL
                        WHERE tenant=? AND subject=? AND idempotency_key=?
                        """,
                        (
                            owner,
                            generation,
                            now + lease_seconds,
                            tenant,
                            subject,
                            idempotency_key,
                        ),
                    )
                    self.connection.commit()
                    return ActionClaim(
                        execute=True,
                        status="started",
                        idempotency_key=idempotency_key,
                        generation=generation,
                    )
                self.connection.execute(
                    """
                    UPDATE actions
                    SET status='status_unknown', lease_expires_at=0
                    WHERE tenant=? AND subject=? AND idempotency_key=?
                    """,
                    (tenant, subject, idempotency_key),
                )
                self.connection.commit()
                raise UnknownActionStatus(
                    "Action lease expired; reconcile with the provider before retrying"
                )
            except Exception:
                self.connection.rollback()
                raise

    def load_completed_action(
        self,
        tenant: str,
        subject: str,
        idempotency_key: str,
        fingerprint: str,
    ) -> ActionClaim | None:
        with self._lock:
            row = self.connection.execute(
                """
                SELECT fingerprint, status, result_json, generation
                FROM actions
                WHERE tenant=? AND subject=? AND idempotency_key=?
                """,
                (tenant, subject, idempotency_key),
            ).fetchone()
        if row is None:
            return None
        if row["fingerprint"] != fingerprint:
            raise ValueError("Idempotency key belongs to another action")
        if row["status"] != "completed":
            return None
        return ActionClaim(
            execute=False,
            status="completed",
            idempotency_key=idempotency_key,
            result=json.loads(row["result_json"]),
            generation=row["generation"],
        )

    def complete_action(
        self,
        tenant: str,
        subject: str,
        idempotency_key: str,
        generation: int,
        result: Any,
    ) -> None:
        with self._lock, self.connection:
            cursor = self.connection.execute(
                """
                UPDATE actions
                SET status='completed', result_json=?, lease_expires_at=0
                WHERE tenant=? AND subject=? AND idempotency_key=?
                    AND generation=? AND status IN ('started', 'status_unknown')
                """,
                (
                    canonical_json(result),
                    tenant,
                    subject,
                    idempotency_key,
                    generation,
                ),
            )
            if cursor.rowcount != 1:
                raise StaleActionClaim("Action claim is no longer current")

    def mark_status_unknown(
        self,
        tenant: str,
        subject: str,
        idempotency_key: str,
        generation: int,
    ) -> ActionClaim:
        with self._lock, self.connection:
            cursor = self.connection.execute(
                """
                UPDATE actions
                SET status='status_unknown', lease_expires_at=0
                WHERE tenant=? AND subject=? AND idempotency_key=?
                    AND generation=? AND status='started'
                """,
                (tenant, subject, idempotency_key, generation),
            )
            if cursor.rowcount != 1:
                raise StaleActionClaim("Action claim is no longer current")
        return ActionClaim(
            execute=False,
            status="status_unknown",
            idempotency_key=idempotency_key,
            generation=generation,
        )

    def mark_action_retryable(
        self,
        tenant: str,
        subject: str,
        idempotency_key: str,
        generation: int,
    ) -> ActionClaim:
        with self._lock, self.connection:
            cursor = self.connection.execute(
                """
                UPDATE actions
                SET status='retryable', generation=generation + 1,
                    lease_expires_at=0, result_json=NULL
                WHERE tenant=? AND subject=? AND idempotency_key=?
                    AND generation=? AND status='status_unknown'
                """,
                (tenant, subject, idempotency_key, generation),
            )
            if cursor.rowcount != 1:
                raise StaleActionClaim("Action claim is no longer current")
        return ActionClaim(
            execute=False,
            status="retryable",
            idempotency_key=idempotency_key,
            generation=generation + 1,
        )

    def reconcile_action(
        self,
        tenant: str,
        subject: str,
        idempotency_key: str,
        fingerprint: str,
        *,
        committed: bool,
        provider_result: Any = None,
    ) -> None:
        with self._lock, self.connection:
            row = self.connection.execute(
                """
                SELECT fingerprint, status, generation FROM actions
                WHERE tenant=? AND subject=? AND idempotency_key=?
                """,
                (tenant, subject, idempotency_key),
            ).fetchone()
            if row is None:
                raise KeyError("Action claim does not exist")
            if row["fingerprint"] != fingerprint:
                raise ValueError("Idempotency key belongs to another action")
            if row["status"] != "status_unknown":
                raise ValueError("Only an action with unknown status can be reconciled")
            if not committed:
                self.connection.execute(
                    """
                    UPDATE actions
                    SET status='retryable', generation=generation + 1,
                        lease_expires_at=0, result_json=NULL
                    WHERE tenant=? AND subject=? AND idempotency_key=?
                    """,
                    (tenant, subject, idempotency_key),
                )
                return
            self.connection.execute(
                """
                UPDATE actions
                SET status='completed', result_json=?, generation=generation + 1,
                    lease_expires_at=0
                WHERE tenant=? AND subject=? AND idempotency_key=?
                """,
                (
                    canonical_json(provider_result),
                    tenant,
                    subject,
                    idempotency_key,
                ),
            )

    def close(self) -> None:
        with self._lock:
            self.connection.close()


class TravelTools:
    """Local tool adapter that models provider-side idempotency."""

    def __init__(self) -> None:
        self.purchases: list[str] = []
        self.provider_results: dict[tuple[str, str, str], str] = {}
        self._purchase_lock = threading.Lock()

    def search_flights(
        self,
        arguments: dict[str, Any],
        context: RunContext,
    ) -> list[str]:
        context.cancellation.raise_if_cancelled()
        destination = str(arguments["destination"])
        return [f"FL-204 to {destination} for $450"]

    def purchase_flight(
        self,
        arguments: dict[str, Any],
        context: RunContext,
    ) -> str:
        context.cancellation.raise_if_cancelled()
        if context.approval is None:
            raise PermissionError("Purchase approval required")
        key = (
            context.identity.tenant,
            context.identity.subject,
            context.approval.idempotency_key,
        )
        with self._purchase_lock:
            if key in self.provider_results:
                return self.provider_results[key]
            flight_id = str(arguments["flight_id"])
            self.purchases.append(flight_id)
            result = f"Purchased {flight_id}"
            self.provider_results[key] = result
            return result

    def check_purchase(
        self,
        idempotency_key: str,
        context: RunContext,
    ) -> ReconciliationResult:
        key = (
            context.identity.tenant,
            context.identity.subject,
            idempotency_key,
        )
        result = self.provider_results.get(key)
        return ReconciliationResult(result is not None, result)


@auth(logged_in=True, roles=["traveler", "travel_admin"])
def search_flights(destination: str) -> list[str]:
    """Find available flights to a destination."""
    raise RuntimeError("The harness owns tool execution")


@auth(logged_in=True, roles=["traveler", "travel_admin"])
def purchase_flight(flight_id: str) -> str:
    """Purchase a selected flight after exact approval."""
    raise RuntimeError("The harness owns tool execution")


def message_to_dict(message: Any) -> dict[str, Any]:
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)
    if isinstance(message, dict):
        return message.copy()
    return dict(message)


class ProductionAgent:
    def __init__(
        self,
        deployment: DeploymentInfo,
        tools: dict[str, ToolSpec],
        store: DurableStore,
        approval_authority: ApprovalAuthority,
        event_sink: EventSink,
        client: Any | None = None,
        max_steps: int = MAX_STEPS,
        model_timeout: float = MODEL_TIMEOUT_SECONDS,
    ):
        self.deployment = deployment
        self.tools = tools
        self.store = store
        self.approval_authority = approval_authority
        self.event_sink = event_sink
        self.client = client
        self.max_steps = max_steps
        self.model_timeout = model_timeout

    def record_event(
        self,
        state: RunState,
        context: RunContext,
        event_type: str,
        **data: Any,
    ) -> None:
        event = {
            "event_id": f"event-{uuid.uuid4().hex}",
            "event_type": event_type,
            "run_id": state.run_id,
            "step": state.step,
            "timestamp": utc_now().isoformat(),
            "agent_version": context.deployment.agent_version,
            "model_version": context.deployment.model,
            "policy_version": context.deployment.policy_version,
            **data,
        }
        state.events.append(event)
        self.store.save_event_checkpoint(state, event)
        self.publish_pending_events()

    def publish_pending_events(self) -> None:
        for event in self.store.load_pending_events():
            try:
                self.event_sink.emit(event)
            except Exception:
                return
            self.store.mark_event_published(event["event_id"])

    def authorize_tool(
        self,
        spec: ToolSpec,
        arguments: dict[str, Any],
        context: RunContext,
    ) -> Approval | None:
        if spec.auth_policy.logged_in and not context.identity.subject:
            raise PermissionError("Tool requires a signed-in user")
        if not context.identity.roles.intersection(spec.allowed_roles):
            raise PermissionError("Identity is not allowed to use this tool")
        if not spec.requires_approval:
            return None
        return self.approval_authority.verify(
            context.approval,
            context.identity,
            spec.name,
            arguments,
        )

    def invoke_tool(
        self,
        spec: ToolSpec,
        arguments: dict[str, Any],
        context: RunContext,
    ) -> Any:
        context.cancellation.raise_if_cancelled()
        timeout = min(spec.timeout_seconds, context.deadline.remaining_seconds())
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(spec.handler, arguments, context)
        try:
            while True:
                context.cancellation.raise_if_cancelled()
                wait_for = min(0.05, context.deadline.remaining_seconds(), timeout)
                try:
                    return future.result(timeout=wait_for)
                except FutureTimeoutError:
                    timeout -= wait_for
                    if timeout <= 0:
                        future.cancel()
                        raise TimeoutError(
                            "Tool execution exceeded its deadline"
                        ) from None
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def invoke_model(
        self,
        state: RunState,
        context: RunContext,
    ) -> ChatResponse:
        remaining = context.deadline.remaining_seconds()
        timeout = min(self.model_timeout, remaining)
        client = self.client or Client(timeout=timeout)
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            client.chat,
            model=context.deployment.model,
            messages=state.messages,
            tools=[spec.schema for spec in self.tools.values()],
            think=False,
        )
        try:
            while True:
                context.cancellation.raise_if_cancelled()
                wait_for = min(0.05, context.deadline.remaining_seconds(), timeout)
                try:
                    return future.result(timeout=wait_for)
                except FutureTimeoutError:
                    timeout -= wait_for
                    if timeout <= 0:
                        future.cancel()
                        raise TimeoutError("Model execution exceeded its deadline") from None
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: RunContext,
    ) -> tuple[Any, bool]:
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
        spec = self.tools[name]
        validate_tool_arguments(spec.schema, arguments)
        if not spec.side_effecting:
            self.authorize_tool(spec, arguments, context)
            return self.invoke_tool(spec, arguments, context), False
        if not context.identity.roles.intersection(spec.allowed_roles):
            raise PermissionError("Identity is not allowed to use this tool")
        if not spec.requires_approval:
            raise PermissionError("Side-effecting tool requires approval")
        approval = self.approval_authority.verify_binding(
            context.approval,
            context.identity,
            name,
            arguments,
        )

        fingerprint = action_fingerprint(name, arguments)
        completed = self.store.load_completed_action(
            context.identity.tenant,
            context.identity.subject,
            approval.idempotency_key,
            fingerprint,
        )
        if completed is not None:
            return completed.result, True
        self.approval_authority.verify_expiry(approval)
        claim = self.store.claim_action(
            context.identity.tenant,
            context.identity.subject,
            approval.idempotency_key,
            fingerprint,
            owner=context.identity.subject,
        )
        if not claim.execute:
            return claim.result, True
        if claim.generation is None:
            raise RuntimeError("Executable action claim requires a generation")
        try:
            result = self.invoke_tool(spec, arguments, context)
        except Exception as error:
            self.store.mark_status_unknown(
                context.identity.tenant,
                context.identity.subject,
                approval.idempotency_key,
                claim.generation,
            )
            raise SideEffectStatusUnknown(
                "External side effect requires provider reconciliation"
            ) from error
        self.store.complete_action(
            context.identity.tenant,
            context.identity.subject,
            approval.idempotency_key,
            claim.generation,
            result,
        )
        return result, False

    def reconcile_action(
        self,
        name: str,
        arguments: dict[str, Any],
        context: RunContext,
    ) -> ReconciliationResult:
        spec = self.tools[name]
        if context.approval is None:
            raise PermissionError("Approval required")
        if spec.reconcile is None:
            raise RuntimeError(f"Tool {name!r} does not support reconciliation")
        evidence = spec.reconcile(
            context.approval.idempotency_key,
            context,
        )
        self.store.reconcile_action(
            context.identity.tenant,
            context.identity.subject,
            context.approval.idempotency_key,
            action_fingerprint(name, arguments),
            provider_result=evidence.result,
            committed=evidence.committed,
        )
        return evidence

    def stop(
        self,
        state: RunState,
        context: RunContext,
        reason: str,
        tool: str | None = None,
    ) -> RunState:
        state.termination_reason = reason
        data = {"reason": reason}
        if tool is not None:
            data["tool"] = tool
        self.record_event(state, context, "run_stopped", **data)
        return state

    def pause_for_reconciliation(
        self,
        state: RunState,
        context: RunContext,
        reason: str,
        tool: str,
    ) -> RunState:
        state.termination_reason = "awaiting_reconciliation"
        self.record_event(
            state,
            context,
            "run_paused",
            reason=reason,
            tool=tool,
        )
        return state

    def continue_pending_tools(
        self,
        state: RunState,
        context: RunContext,
    ) -> RunState | None:
        while state.pending_tool_calls:
            pending = state.pending_tool_calls[0]
            name = str(pending["name"])
            arguments = dict(pending["arguments"])
            if pending["status"] == "proposed":
                pending["status"] = "requested"
                self.record_event(
                    state,
                    context,
                    "tool_requested",
                    tool=name,
                    arguments_hash=action_fingerprint(name, arguments),
                )
            try:
                result, replayed = self.execute_tool(name, arguments, context)
            except PermissionError as error:
                reason_codes = {
                    "Approval required": "approval_required",
                    "Approval has expired": "approval_expired",
                    "Approval signature is invalid": "approval_invalid",
                }
                self.record_event(
                    state,
                    context,
                    "policy_denied",
                    tool=name,
                    reason_code=reason_codes.get(str(error), "policy_denied"),
                )
                return self.stop(state, context, "policy_denied", tool=name)
            except CancelledError:
                if self.tools[name].side_effecting:
                    return self.pause_for_reconciliation(
                        state,
                        context,
                        "tool_status_unknown",
                        name,
                    )
                return self.stop(state, context, "cancelled", tool=name)
            except TimeoutError:
                if self.tools[name].side_effecting:
                    return self.pause_for_reconciliation(
                        state,
                        context,
                        "tool_timeout",
                        name,
                    )
                return self.stop(state, context, "tool_timeout", tool=name)
            except UnknownActionStatus:
                return self.pause_for_reconciliation(
                    state,
                    context,
                    "tool_status_unknown",
                    name,
                )
            except SideEffectStatusUnknown as error:
                self.record_event(
                    state,
                    context,
                    "tool_failed",
                    tool=name,
                    error_type=type(error.__cause__).__name__,
                )
                return self.pause_for_reconciliation(
                    state,
                    context,
                    "tool_status_unknown",
                    name,
                )
            except ActionInProgress:
                return self.pause_for_reconciliation(
                    state,
                    context,
                    "tool_in_progress",
                    name,
                )
            except Exception as error:
                self.record_event(
                    state,
                    context,
                    "tool_failed",
                    tool=name,
                    error_type=type(error).__name__,
                )
                return self.stop(state, context, "tool_error", tool=name)

            state.messages.append(
                {
                    "role": "tool",
                    "tool_name": name,
                    "content": str(result),
                }
            )
            state.pending_tool_calls.pop(0)
            self.record_event(
                state,
                context,
                "tool_completed",
                tool=name,
                replayed=replayed,
            )
        return None

    def run(
        self,
        task: str,
        context: RunContext,
        run_id: str | None = None,
    ) -> RunState:
        self.publish_pending_events()
        state = self.store.load_checkpoint(run_id) if run_id else None
        if state is not None:
            if (
                state.subject != context.identity.subject
                or state.tenant != context.identity.tenant
            ):
                raise PermissionError("Run belongs to another identity")
            if state.termination_reason == "awaiting_reconciliation":
                state.termination_reason = None
            if state.termination_reason is not None:
                return state
            self.record_event(state, context, "run_resumed")
        else:
            state = RunState(
                run_id=run_id or f"run-{uuid.uuid4().hex[:12]}",
                messages=[
                    {
                        "role": "system",
                        "content": "Use the supplied travel tools to complete the task.",
                    },
                    {"role": "user", "content": task},
                ],
                subject=context.identity.subject,
                tenant=context.identity.tenant,
            )
            self.record_event(state, context, "run_started")

        while state.step < self.max_steps:
            stopped = self.continue_pending_tools(state, context)
            if stopped is not None:
                return stopped
            try:
                context.cancellation.raise_if_cancelled()
                context.deadline.remaining_seconds()
                self.record_event(state, context, "model_requested")
                response = self.invoke_model(state, context)
            except CancelledError:
                return self.stop(state, context, "cancelled")
            except (TimeoutError, TimeoutException):
                return self.stop(state, context, "model_timeout")
            except (ConnectionError, ResponseError):
                return self.stop(state, context, "model_error")

            state.messages.append(message_to_dict(response.message))
            state.step += 1

            if not response.message.tool_calls:
                state.final_answer = response.message.content
                state.termination_reason = "completed"
                self.record_event(state, context, "run_completed")
                return state

            state.pending_tool_calls = [
                {
                    "name": call.function.name,
                    "arguments": dict(call.function.arguments),
                    "status": "proposed",
                }
                for call in response.message.tool_calls
            ]
            self.store.save_checkpoint(state)

        return self.stop(state, context, "max_steps")


def build_agent(
    database: str | Path,
    events: str | Path,
    deployment_path: str | Path,
    approval_secret: str,
    client: Any | None = None,
) -> tuple[ProductionAgent, TravelTools, ApprovalAuthority]:
    deployment = DeploymentInfo.load(deployment_path)
    travel_tools = TravelTools()
    authority = ApprovalAuthority(approval_secret)
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
        store=DurableStore(database),
        approval_authority=authority,
        event_sink=JsonLinesEventSink(events),
        client=client,
    )
    return agent, travel_tools, authority


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Chapter 18 travel agent")
    parser.add_argument(
        "task",
        nargs="?",
        default="Find a flight to Paris",
    )
    parser.add_argument("--approve-flight")
    parser.add_argument("--database", default="agent.db")
    parser.add_argument("--events", default="events.jsonl")
    parser.add_argument("--deployment", default="deployment.json")
    parser.add_argument(
        "--run-id",
        help="Resume a nonterminal checkpoint or assign an ID to a new run",
    )
    args = parser.parse_args()

    secret = os.environ.get("APPROVAL_SIGNING_SECRET", "local-development-only")
    agent, tools, authority = build_agent(
        args.database,
        args.events,
        args.deployment,
        secret,
    )
    identity = Identity(
        subject="user-1842",
        tenant="travel",
        roles=frozenset({"traveler"}),
    )
    approval = None
    if args.approve_flight:
        approval = authority.issue(
            identity,
            "purchase_flight",
            {"flight_id": args.approve_flight},
            f"purchase-{args.approve_flight}-{identity.subject}",
        )
    context = RunContext(
        identity=identity,
        deployment=agent.deployment,
        deadline=Deadline.after(60.0),
        cancellation=CancellationToken(),
        approval=approval,
    )
    state = agent.run(args.task, context, run_id=args.run_id)
    print(json.dumps(asdict(state), indent=2))
    print(f"Purchases: {tools.purchases}")


if __name__ == "__main__":
    main()
