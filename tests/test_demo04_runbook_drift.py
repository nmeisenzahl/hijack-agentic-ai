"""Demo 04 preflight test — Runbook Drift (poisoned log line widens remediation plan).

Run this file from the repository root so it executes in its own pytest
process and avoids cross-demo module contamination:

    pytest tests/test_demo04_runbook_drift.py -v

Asserts:
  - the trusted runbook parses and defines a narrow, ordered fallback
  - invalid runbook IDs, error classes, and out-of-scope actions fail before runtime
  - the checked-in alert parses and selects the RB-500 runbook
  - the operations API exposes state, logs, health, and action endpoints
  - the poisoner payload contains the expected dangerous action markers
  - the Compose wiring orders poisoner before agent and mounts data read-only
  - SECURITY_ENABLED parsing is strict and fails closed on unsupported values
  - the AGT declared-intent layer declares the runbook scope as parent intent,
    rejects widened remediation plans atomically, and falls back to the
    trusted runbook steps
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path("demos/04-runbook-drift/agent")))
sys.path.insert(0, str(Path("demos/04-runbook-drift")))
sys.path.insert(0, str(Path("demos/04-runbook-drift/ops-api")))

from agent.runbook import load_alert, load_runbook

DEMO_DIR = Path("demos/04-runbook-drift")
RUNBOOK_FILE = DEMO_DIR / "data" / "runbook-RB-500.yaml"
ALERT_FILE = DEMO_DIR / "data" / "alert-9042.json"


@pytest.fixture
def ops_api(monkeypatch):
    seed_path = DEMO_DIR / "data" / "access.log.seed"
    monkeypatch.setenv("ACCESS_LOG_SEED", str(seed_path))
    import main

    importlib.reload(main)
    main.STATE["audit_enabled"] = True
    main.STATE["users"].clear()
    main.STATE["restarts"].clear()
    main.STATE["escalations"].clear()
    main.ACCESS_LOG[:] = []
    main.load_seed_log()
    from fastapi.testclient import TestClient

    yield TestClient(main.app)


def test_runbook_defines_scope_and_ordered_fallback():
    runbook = load_runbook(RUNBOOK_FILE, "RB-500", "5xx-ORD")
    assert runbook.permitted_actions == [
        "read_logs",
        "restart_service",
        "escalate_to_human",
    ]
    assert [step.action for step in runbook.safe_fallback_steps] == [
        "restart_service",
        "escalate_to_human",
    ]


def test_runbook_rejects_fallback_outside_scope(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        "runbook_id: RB-500\n"
        "error_class: 5xx-ORD\n"
        "permitted_actions: [read_logs]\n"
        "safe_fallback_steps:\n"
        "  - action: create_admin_user\n"
        "    params: {username: svc-recovery}\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="outside permitted_actions"):
        load_runbook(path, "RB-500", "5xx-ORD")


def test_runbook_rejects_id_mismatch():
    with pytest.raises(RuntimeError, match="Runbook ID mismatch"):
        load_runbook(RUNBOOK_FILE, "RB-999", "5xx-ORD")


def test_runbook_rejects_error_class_mismatch():
    with pytest.raises(RuntimeError, match="Runbook error class mismatch"):
        load_runbook(RUNBOOK_FILE, "RB-500", "authz-FAIL")


def test_alert_parses_and_selects_runbook():
    alert = load_alert(ALERT_FILE)
    assert alert.alert_id == "9042"
    assert alert.service == "checkout-service"
    assert alert.error_class == "5xx-ORD"
    assert alert.runbook_id == "RB-500"


def test_ops_api_initial_state(ops_api):
    assert ops_api.get("/state").json() == {
        "audit_enabled": True,
        "users": [],
        "restarts": [],
        "escalations": [],
    }


def test_ops_api_health_and_seed_log(ops_api):
    logs = ops_api.get("/logs").json()["lines"]
    assert any("GET /health HTTP/1.1" in line for line in logs)

    health = ops_api.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "healthy"}

    logs_after = ops_api.get("/logs").json()["lines"]
    assert len(logs_after) > len(logs)
    assert any("GET /health" in line and 'UA:"testclient"' in line for line in logs_after)


def test_ops_api_restart_service(ops_api):
    response = ops_api.post("/actions/restart_service", json={"service": "checkout-service"})
    assert response.status_code == 200
    assert ops_api.get("/state").json()["restarts"] == [{"service": "checkout-service"}]


def test_ops_api_escalate_to_human(ops_api):
    response = ops_api.post("/actions/escalate_to_human", json={"team": "sre"})
    assert response.status_code == 200
    assert ops_api.get("/state").json()["escalations"] == [{"team": "sre"}]


def test_ops_api_disable_audit_logging(ops_api):
    response = ops_api.post("/actions/disable_audit_logging")
    assert response.status_code == 200
    assert ops_api.get("/state").json()["audit_enabled"] is False


def test_ops_api_create_admin_user(ops_api):
    response = ops_api.post("/actions/create_admin_user", json={"username": "svc-recovery"})
    assert response.status_code == 200
    assert ops_api.get("/state").json()["users"] == [
        {"username": "svc-recovery", "role": "admin"}
    ]


def test_ops_api_create_admin_user_rejects_empty_username(ops_api):
    response = ops_api.post("/actions/create_admin_user", json={"username": ""})
    assert response.status_code == 400


def test_access_log_sanitizes_embedded_crlf(ops_api):
    ops_api.get("/logs")  # ensure client wiring works
    import asyncio

    import main

    baseline = len(main.ACCESS_LOG)
    # Crafted ASGI scope carrying raw CR/LF in the request target fields.
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET\r\nFORGED 200 OK",
        "scheme": "http",
        "path": "/logs\r\nFAKE 200 OK",
        "raw_path": b"/logs%0d%0aFAKE%20200%20OK",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"user-agent", b"evil-agent")],
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        return None

    asyncio.run(main.app(scope, receive, send))

    new_lines = main.ACCESS_LOG[baseline:]
    assert new_lines
    for line in new_lines:
        assert "\r" not in line
        assert "\n" not in line
    assert any("\\r\\n" in line for line in new_lines)


def test_poisoner_payload_names_both_dangerous_actions():
    payload = (DEMO_DIR / "poisoner" / "send.py").read_text()
    assert "disable_audit_logging" in payload
    assert "create_admin_user" in payload
    assert "svc-recovery" in payload
    assert "Do not escalate" in payload


def test_compose_orders_poisoner_before_agent():
    compose = (DEMO_DIR / "docker-compose.yml").read_text()
    assert "condition: service_healthy" in compose
    assert "condition: service_completed_successfully" in compose
    assert "SECURITY_ENABLED_OVERRIDE=${SECURITY_ENABLED:-}" in compose
    assert "./data:/app/data:ro" in compose


# ---------------------------------------------------------------------------
# AGT (agent-os 5.0.0) test double implementing the declared-intent contract
# ---------------------------------------------------------------------------


class IntentScopeError(Exception):
    pass


class IntentAction:
    def __init__(self, action, params_schema=None):
        self.action = action
        self.params_schema = params_schema


class FakeDriftPolicy:
    SOFT_BLOCK = "soft_block"
    HARD_BLOCK = "hard_block"
    RE_DECLARE = "re_declare"


class FakeMemoryBackend:
    pass


class FakeIntent:
    def __init__(
        self,
        intent_id,
        agent_id,
        planned_actions,
        parent_intent_id=None,
        state="declared",
    ):
        self.intent_id = intent_id
        self.agent_id = agent_id
        self.planned_actions = planned_actions
        self.parent_intent_id = parent_intent_id
        self.state = state
        self.execution_records = []

    @property
    def planned_action_names(self):
        return {item.action for item in self.planned_actions}


class FakeIntentManager:
    instances = []

    def __init__(self, backend):
        self.backend = backend
        self.events = []
        self.intents = {}
        self.counter = 0
        FakeIntentManager.instances.append(self)

    async def declare_intent(
        self,
        agent_id,
        planned_actions,
        drift_policy=None,
        parent_intent_id=None,
        ttl_seconds=None,
    ):
        if parent_intent_id is not None:
            parent = self.intents[parent_intent_id]
            excess = {
                item.action for item in planned_actions
            } - parent.planned_action_names
            if excess:
                raise IntentScopeError(
                    f"Child intent cannot expand parent scope. Excess actions: {excess}"
                )
        self.counter += 1
        intent = FakeIntent(
            intent_id=f"intent:{self.counter}",
            agent_id=agent_id,
            planned_actions=planned_actions,
            parent_intent_id=parent_intent_id,
        )
        self.intents[intent.intent_id] = intent
        self.events.append(
            ("declare", agent_id, [item.action for item in planned_actions])
        )
        return intent

    async def approve_intent(self, intent_id):
        intent = self.intents[intent_id]
        intent.state = "approved"
        self.events.append(("approve", intent_id))
        return intent

    async def create_child_intent(
        self,
        parent_intent_id,
        agent_id,
        planned_actions,
        drift_policy=None,
        ttl_seconds=None,
    ):
        return await self.declare_intent(
            agent_id=agent_id,
            planned_actions=planned_actions,
            drift_policy=drift_policy,
            parent_intent_id=parent_intent_id,
            ttl_seconds=ttl_seconds,
        )

    async def check_action(self, intent_id, action, params, agent_id, request_id):
        intent = self.intents[intent_id]
        planned = action in intent.planned_action_names
        intent.state = "executing"
        intent.execution_records.append((action, planned))
        self.events.append(("check", agent_id, action))
        return types.SimpleNamespace(
            allowed=planned,
            was_planned=planned,
            reason="" if planned else f"Action '{action}' not in declared plan",
        )

    async def verify_intent(self, intent_id):
        intent = self.intents[intent_id]
        executed = [
            action for action, planned in intent.execution_records if planned
        ]
        intent.state = "completed"
        return types.SimpleNamespace(
            intent_id=intent_id,
            agent_id=intent.agent_id,
            planned_actions=sorted(intent.planned_action_names),
            executed_actions=executed,
            unplanned_actions=[],
            missed_actions=sorted(intent.planned_action_names - set(executed)),
            total_drift_events=0,
            total_trust_penalty=0.0,
            state=types.SimpleNamespace(value="completed"),
        )

    async def get_intent(self, intent_id):
        return self.intents.get(intent_id)


def _fake_agent_os_modules() -> dict[str, types.ModuleType]:
    agent_os = types.ModuleType("agent_os")
    agent_os.__path__ = []
    intent_module = types.ModuleType("agent_os.intent")
    intent_module.IntentAction = IntentAction
    intent_module.IntentScopeError = IntentScopeError
    intent_module.IntentManager = FakeIntentManager
    intent_module.DriftPolicy = FakeDriftPolicy
    stateless_module = types.ModuleType("agent_os.stateless")
    stateless_module.MemoryBackend = FakeMemoryBackend
    return {
        "agent_os": agent_os,
        "agent_os.intent": intent_module,
        "agent_os.stateless": stateless_module,
    }


@pytest.fixture
def fake_agt():
    """Patch the AGT modules for the duration of one test."""
    FakeIntentManager.instances.clear()
    with patch.dict(sys.modules, _fake_agent_os_modules()):
        yield


# NOTE: tests/conftest.py evicts demo modules (agent, agent.*, security.*)
# from sys.modules after every test, so model classes must be imported inside
# each test/fixture to keep pydantic class identities consistent.

async def _create_runtime(runbook, enabled: bool = True):
    from agent.security.intent_policy import IntentRuntime

    return await IntentRuntime.create(enabled=enabled, runbook=runbook)


def _proposed_plan(*actions: str):
    from agent.models import PlannedStep, ProposedRemediationPlan

    return ProposedRemediationPlan(
        alert_id="9042",
        steps=[PlannedStep(action=action) for action in actions],
        summary="test plan",
    )


class TestSecurityMode:
    def test_normalize_accepts_true_and_false(self):
        from agent.security.runtime import normalize_security_enabled

        assert normalize_security_enabled("true") is True
        assert normalize_security_enabled(" TRUE ") is True
        assert normalize_security_enabled("false") is False
        assert normalize_security_enabled(" False ") is False

    @pytest.mark.parametrize("raw", ["all", "policy", "yes", "1", ""])
    def test_normalize_rejects_unsupported_modes(self, raw):
        from agent.security.runtime import normalize_security_enabled

        with pytest.raises(RuntimeError, match="Unsupported SECURITY_ENABLED"):
            normalize_security_enabled(raw)

    def test_resolve_prefers_non_empty_override(self, monkeypatch):
        from agent.security.runtime import resolve_security_enabled

        monkeypatch.setenv("SECURITY_ENABLED", "false")
        monkeypatch.setenv("SECURITY_ENABLED_OVERRIDE", "true")
        assert resolve_security_enabled() is True
        monkeypatch.setenv("SECURITY_ENABLED_OVERRIDE", "   ")
        assert resolve_security_enabled() is False

    def test_resolve_defaults_to_false(self, monkeypatch):
        from agent.security.runtime import resolve_security_enabled

        monkeypatch.delenv("SECURITY_ENABLED", raising=False)
        monkeypatch.delenv("SECURITY_ENABLED_OVERRIDE", raising=False)
        assert resolve_security_enabled() is False

    def test_resolve_fails_closed_on_invalid_env(self, monkeypatch):
        from agent.security.runtime import resolve_security_enabled

        monkeypatch.setenv("SECURITY_ENABLED", "policy")
        monkeypatch.delenv("SECURITY_ENABLED_OVERRIDE", raising=False)
        with pytest.raises(RuntimeError, match="Unsupported SECURITY_ENABLED"):
            resolve_security_enabled()


class TestIntentPolicy:
    @pytest.fixture
    def runbook(self):
        from agent.runbook import load_runbook

        return load_runbook(RUNBOOK_FILE, "RB-500", "5xx-ORD")

    async def test_disabled_mode_never_instantiates_agt(self, runbook, fake_agt):
        from agent.security.intent_policy import IntentRuntime

        runtime = await IntentRuntime.create(enabled=False, runbook=runbook)
        assert runtime.enabled is False
        assert runtime.manager is None
        assert runtime.parent_intent_id is None
        assert runtime.commander_intent_id is None
        assert runtime.remediation_intent_id is None
        assert FakeIntentManager.instances == []

    async def test_disabled_mode_passes_plan_through_unchecked(self, runbook, fake_agt):
        runtime = await _create_runtime(runbook, enabled=False)
        plan = _proposed_plan("disable_audit_logging", "create_admin_user")
        execution = await runtime.authorize_plan(plan)
        assert execution.authorization_status == "disabled"
        assert execution.fallback_used is False
        assert execution.refused == []
        assert execution.intent_id is None
        assert [step.action for step in execution.steps] == [
            "disable_audit_logging",
            "create_admin_user",
        ]
        await runtime.check_commander_action("create_admin_user", {})
        await runtime.check_remediation_action(None, "create_admin_user", {})
        assert await runtime.verify_children() == []

    async def test_parent_declared_and_approved_before_commander_child(self, runbook, fake_agt):
        runtime = await _create_runtime(runbook)
        manager = runtime.manager
        assert manager.events[:4] == [
            ("declare", "incident_workflow", runbook.permitted_actions),
            ("approve", runtime.parent_intent_id),
            ("declare", "incident_commander", ["read_logs"]),
            ("approve", runtime.commander_intent_id),
        ]
        parent = manager.intents[runtime.parent_intent_id]
        commander = manager.intents[runtime.commander_intent_id]
        assert parent.agent_id == "incident_workflow"
        assert parent.planned_action_names == set(runbook.permitted_actions)
        assert commander.planned_action_names == {"read_logs"}
        assert commander.parent_intent_id == parent.intent_id
        assert parent.state == "approved"
        assert commander.state == "approved"

    async def test_clean_plan_approved_as_proposed(self, runbook, fake_agt):
        runtime = await _create_runtime(runbook)
        execution = await runtime.authorize_plan(
            _proposed_plan("read_logs", "restart_service")
        )
        assert execution.fallback_used is False
        assert execution.refused == []
        assert execution.authorization_status == "approved_as_proposed"
        assert [step.action for step in execution.steps] == [
            "read_logs",
            "restart_service",
        ]
        child = runtime.manager.intents[execution.intent_id]
        assert child.agent_id == "remediation_agent"
        assert child.state == "approved"
        assert child.parent_intent_id == runtime.parent_intent_id
        assert runtime.remediation_intent_id == child.intent_id

    async def test_injected_plan_rejected_atomically_with_fallback(self, runbook, fake_agt):
        runtime = await _create_runtime(runbook)
        manager = runtime.manager
        intents_before = set(manager.intents)
        execution = await runtime.authorize_plan(
            _proposed_plan(
                "read_logs",
                "restart_service",
                "disable_audit_logging",
                "create_admin_user",
            )
        )
        assert execution.fallback_used is True
        assert execution.authorization_status == "approved_fallback"
        assert execution.refused == ["create_admin_user", "disable_audit_logging"]
        assert [step.action for step in execution.steps] == [
            "restart_service",
            "escalate_to_human",
        ]
        assert execution.intent_id == runtime.remediation_intent_id

        # Atomic rejection: exactly one new intent exists (the fallback child);
        # no intent was ever persisted for the poisoned plan.
        new_intents = [
            intent
            for intent_id, intent in manager.intents.items()
            if intent_id not in intents_before
        ]
        assert len(new_intents) == 1
        fallback_child = new_intents[0]
        assert fallback_child.intent_id == execution.intent_id
        assert fallback_child.state == "approved"
        assert [item.action for item in fallback_child.planned_actions] == [
            "restart_service",
            "escalate_to_human",
        ]
        remediation_declares = [
            event for event in manager.events
            if event[0] == "declare" and event[1] == "remediation_agent"
        ]
        assert remediation_declares == [
            ("declare", "remediation_agent", ["restart_service", "escalate_to_human"])
        ]

    async def test_denied_actions_raise_intent_action_denied(self, runbook, fake_agt):
        from agent.security.intent_policy import IntentActionDenied

        runtime = await _create_runtime(runbook)
        with pytest.raises(IntentActionDenied, match="create_admin_user"):
            await runtime.check_commander_action("create_admin_user", {})
        await runtime.check_commander_action("read_logs", {})

        execution = await runtime.authorize_plan(
            _proposed_plan("disable_audit_logging", "create_admin_user")
        )
        with pytest.raises(IntentActionDenied) as excinfo:
            await runtime.check_remediation_action(
                execution.intent_id, "disable_audit_logging", {}
            )
        assert excinfo.value.action == "disable_audit_logging"
        assert "not in declared plan" in excinfo.value.reason
        await runtime.check_remediation_action(
            execution.intent_id,
            "restart_service",
            {"service": "checkout-service"},
        )

    async def test_verify_children_covers_children_not_parent(self, runbook, fake_agt):
        runtime = await _create_runtime(runbook)
        await runtime.check_commander_action("read_logs", {})
        execution = await runtime.authorize_plan(
            _proposed_plan("disable_audit_logging", "create_admin_user")
        )
        await runtime.check_remediation_action(
            execution.intent_id,
            "restart_service",
            {"service": "checkout-service"},
        )
        verifications = await runtime.verify_children()
        assert [v.agent_id for v in verifications] == [
            "incident_commander",
            "remediation_agent",
        ]
        commander_v, remediation_v = verifications
        assert commander_v.planned_actions == ["read_logs"]
        assert commander_v.executed_actions == ["read_logs"]
        assert commander_v.missed_actions == []
        assert remediation_v.planned_actions == [
            "escalate_to_human",
            "restart_service",
        ]
        assert remediation_v.executed_actions == ["restart_service"]
        assert remediation_v.unplanned_actions == []
        assert remediation_v.missed_actions == ["escalate_to_human"]
        assert remediation_v.total_drift_events == 0
        # The parent is rendered separately, never as a recursively verified child.
        assert runtime.parent_intent_id not in {
            v.intent_id for v in verifications
        }


# ---------------------------------------------------------------------------
# Governed tools and deterministic Flock engines (Task 4)
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeHttpClient:
    """Fake async ops-api client recording `http:<action>` events."""

    def __init__(self, events, fail_actions=()):
        self.events = events
        self.fail_actions = set(fail_actions)

    async def post(self, url, json=None):
        action = url.rsplit("/", 1)[-1]
        if action in self.fail_actions:
            raise RuntimeError("simulated ops-api outage")
        self.events.append(f"http:{action}")
        return _FakeResponse({"ok": True, "action": action, "params": json or {}})

    async def get(self, url):
        assert url.endswith("/logs")
        self.events.append("http:read_logs")
        return _FakeResponse({"lines": ["line-1", "line-2"]})


class _FakeToolRuntime:
    """Declared-intent test double recording `check:<action>` events."""

    def __init__(self, events):
        self.events = events
        self.denied = set()
        self.remediation_intent_id = "intent:test"

    def deny(self, action):
        self.denied.add(action)

    async def check_commander_action(self, action, params):
        self.events.append(f"check:{action}")
        if action in self.denied:
            from agent.security.intent_policy import IntentActionDenied

            raise IntentActionDenied(action, "denied by test double")

    async def check_remediation_action(self, intent_id, action, params):
        assert intent_id == self.remediation_intent_id
        self.events.append(f"check:{action}")
        if action in self.denied:
            from agent.security.intent_policy import IntentActionDenied

            raise IntentActionDenied(action, "denied by test double")


@pytest.fixture
def configured_tools():
    """Fresh agent.tools module wired to a fake runtime and fake HTTP client."""
    import agent.tools as tools

    events = []
    runtime = _FakeToolRuntime(events)
    tools.configure_intent_runtime(runtime)
    tools.set_http_client(_FakeHttpClient(events))
    return types.SimpleNamespace(
        module=tools,
        runtime=runtime,
        events=events,
        read_logs=tools.read_logs,
        restart_service=tools.restart_service,
        escalate_to_human=tools.escalate_to_human,
        disable_audit_logging=tools.disable_audit_logging,
        create_admin_user=tools.create_admin_user,
    )


class TestGovernedTools:
    async def test_read_logs_checks_commander_intent_before_http(self, configured_tools):
        lines = await configured_tools.read_logs()
        assert lines == ["line-1", "line-2"]
        assert configured_tools.events == ["check:read_logs", "http:read_logs"]

    async def test_secure_tool_checks_before_http(self, configured_tools):
        events = configured_tools.events
        await configured_tools.restart_service(service="orders-api")
        assert events == ["check:restart_service", "http:restart_service"]

    async def test_denied_tool_never_calls_http(self, configured_tools):
        from agent.security.intent_policy import IntentActionDenied

        configured_tools.runtime.deny("create_admin_user")
        with pytest.raises(IntentActionDenied):
            await configured_tools.create_admin_user(username="svc-recovery")
        assert "http:create_admin_user" not in configured_tools.events

    async def test_tools_fail_closed_without_configured_runtime(self):
        import agent.tools as tools

        with pytest.raises(RuntimeError, match="Intent runtime has not been configured"):
            await tools.restart_service(service="orders-api")

    async def test_business_signatures_hide_intent_ids(self, configured_tools):
        import inspect

        assert list(inspect.signature(configured_tools.restart_service).parameters) == ["service"]
        assert list(inspect.signature(configured_tools.escalate_to_human).parameters) == ["team"]
        assert list(inspect.signature(configured_tools.disable_audit_logging).parameters) == []
        assert list(inspect.signature(configured_tools.create_admin_user).parameters) == ["username"]
        assert list(inspect.signature(configured_tools.read_logs).parameters) == []


class _FakeGateRuntime:
    """authorize_plan test double returning a canned ExecutionPlan."""

    def __init__(self, execution):
        self.execution = execution
        self.seen = None

    async def authorize_plan(self, proposal):
        self.seen = proposal
        return self.execution


def _engine_inputs(model_instance):
    from flock.core.artifacts import Artifact
    from flock.utils.runtime import EvalInputs

    artifact = Artifact(
        type=type(model_instance).__name__,
        payload=model_instance.model_dump(),
        produced_by="test",
    )
    return EvalInputs(artifacts=[artifact])


def _engine_agent(name, tool_functions=()):
    return types.SimpleNamespace(name=name, tools=list(tool_functions))


async def run_remediation_with_failure(fail_action):
    import agent.tools as tools
    from agent.engines import RemediationEngine
    from agent.models import ExecutionPlan, PlannedStep, RemediationOutcome

    events = []
    runtime = _FakeToolRuntime(events)
    tools.configure_intent_runtime(runtime)
    tools.set_http_client(_FakeHttpClient(events, fail_actions={fail_action}))
    agent = _engine_agent(
        "remediation_agent",
        [
            tools.restart_service,
            tools.escalate_to_human,
            tools.disable_audit_logging,
            tools.create_admin_user,
        ],
    )
    plan = ExecutionPlan(
        alert_id="9042",
        steps=[
            PlannedStep(action="restart_service", params={"service": "checkout-service"}),
            PlannedStep(action="escalate_to_human", params={"team": "sre"}),
        ],
        authorization_status="approved_as_proposed",
    )
    engine = RemediationEngine()
    result = await engine.evaluate(agent, None, _engine_inputs(plan), None)
    return RemediationOutcome(**result.artifacts[0].payload)


class TestDeterministicEngines:
    async def test_intent_gate_authorizes_proposal_via_runtime(self):
        from agent.engines import IntentGateEngine
        from agent.models import (
            ExecutionPlan,
            PlannedStep,
            ProposedRemediationPlan,
        )

        proposal = ProposedRemediationPlan(
            alert_id="9042",
            steps=[PlannedStep(action="restart_service", params={"service": "checkout-service"})],
            summary="restart the service",
        )
        execution = ExecutionPlan(
            alert_id="9042",
            steps=[
                PlannedStep(action="restart_service", params={"service": "checkout-service"}),
                PlannedStep(action="escalate_to_human", params={"team": "sre"}),
            ],
            refused=["create_admin_user"],
            fallback_used=True,
            authorization_status="approved_fallback",
            intent_id="intent:fallback",
        )
        runtime = _FakeGateRuntime(execution)
        engine = IntentGateEngine(intent_runtime=runtime)
        agent = _engine_agent("intent_gate")

        result = await engine.evaluate(agent, None, _engine_inputs(proposal), None)

        assert runtime.seen == proposal
        assert len(result.artifacts) == 1
        assert ExecutionPlan(**result.artifacts[0].payload) == execution
        assert result.artifacts[0].produced_by == "intent_gate"

    async def test_intent_gate_requires_a_proposal(self):
        from agent.engines import IntentGateEngine

        runtime = _FakeGateRuntime(None)
        engine = IntentGateEngine(intent_runtime=runtime)
        with pytest.raises(RuntimeError, match="intent_gate received no ProposedRemediationPlan"):
            await engine.evaluate(
                _engine_agent("intent_gate"), None, _engine_inputs_without_artifacts(), None
            )
        assert runtime.seen is None

    async def test_remediation_continues_to_escalation_after_restart_failure(self):
        outcome = await run_remediation_with_failure("restart_service")
        assert outcome.failed == ["restart_service: simulated ops-api outage"]
        assert outcome.executed == ["escalate_to_human"]
        assert outcome.escalated is True

    async def test_remediation_reports_unregistered_tool_and_continues(self):
        import agent.tools as tools
        from agent.engines import RemediationEngine
        from agent.models import ExecutionPlan, PlannedStep, RemediationOutcome

        events = []
        tools.configure_intent_runtime(_FakeToolRuntime(events))
        tools.set_http_client(_FakeHttpClient(events))
        agent = _engine_agent("remediation_agent", [tools.escalate_to_human])
        plan = ExecutionPlan(
            alert_id="9042",
            steps=[
                PlannedStep(action="restart_service", params={"service": "checkout-service"}),
                PlannedStep(action="escalate_to_human", params={"team": "sre"}),
            ],
            authorization_status="approved_as_proposed",
        )
        engine = RemediationEngine()
        result = await engine.evaluate(agent, None, _engine_inputs(plan), None)
        outcome = RemediationOutcome(**result.artifacts[0].payload)

        assert outcome.failed == ["restart_service: tool not registered"]
        assert outcome.executed == ["escalate_to_human"]
        assert outcome.escalated is True

    async def test_remediation_refuses_denied_action_and_merges_gate_refusals(self):
        import agent.tools as tools
        from agent.engines import RemediationEngine
        from agent.models import ExecutionPlan, PlannedStep, RemediationOutcome

        events = []
        runtime = _FakeToolRuntime(events)
        runtime.deny("escalate_to_human")
        tools.configure_intent_runtime(runtime)
        tools.set_http_client(_FakeHttpClient(events))
        agent = _engine_agent(
            "remediation_agent",
            [tools.restart_service, tools.escalate_to_human],
        )
        plan = ExecutionPlan(
            alert_id="9042",
            steps=[
                PlannedStep(action="restart_service", params={"service": "checkout-service"}),
                PlannedStep(action="escalate_to_human", params={"team": "sre"}),
            ],
            refused=["create_admin_user"],
            fallback_used=True,
            authorization_status="approved_fallback",
            intent_id="intent:fallback",
        )
        engine = RemediationEngine()
        result = await engine.evaluate(agent, None, _engine_inputs(plan), None)
        outcome = RemediationOutcome(**result.artifacts[0].payload)

        assert outcome.executed == ["restart_service"]
        assert outcome.refused == ["create_admin_user", "escalate_to_human"]
        assert outcome.failed == []
        assert outcome.escalated is False
        assert "http:escalate_to_human" not in events

    async def test_remediation_drops_model_invented_params(self):
        from agent.engines import RemediationEngine
        from agent.models import ExecutionPlan, PlannedStep, RemediationOutcome

        received = []

        async def restart_service(service: str):
            received.append({"service": service})

        agent = _engine_agent("remediation_agent", [restart_service])
        plan = ExecutionPlan(
            alert_id="9042",
            steps=[
                PlannedStep(
                    action="restart_service",
                    params={
                        "service": "x",
                        "approved": True,
                        "alert_id": "9042",
                    },
                ),
            ],
            authorization_status="approved_as_proposed",
        )
        engine = RemediationEngine()
        result = await engine.evaluate(agent, None, _engine_inputs(plan), None)
        outcome = RemediationOutcome(**result.artifacts[0].payload)

        assert outcome.executed == ["restart_service"]
        assert outcome.failed == []
        assert received == [{"service": "x"}]

    async def test_remediation_records_missing_required_parameter(self):
        from agent.engines import RemediationEngine
        from agent.models import ExecutionPlan, PlannedStep, RemediationOutcome

        async def restart_service(service: str):
            raise AssertionError("tool must not run without its required param")

        agent = _engine_agent("remediation_agent", [restart_service])
        plan = ExecutionPlan(
            alert_id="9042",
            steps=[
                PlannedStep(
                    action="restart_service",
                    params={"approved": True},
                ),
            ],
            authorization_status="approved_as_proposed",
        )
        engine = RemediationEngine()
        result = await engine.evaluate(agent, None, _engine_inputs(plan), None)
        outcome = RemediationOutcome(**result.artifacts[0].payload)

        assert outcome.failed == [
            "restart_service: missing required parameter service"
        ]
        assert outcome.executed == []

    async def test_remediation_requires_an_execution_plan(self):
        from agent.engines import RemediationEngine

        engine = RemediationEngine()
        with pytest.raises(RuntimeError, match="remediation_agent received no ExecutionPlan"):
            await engine.evaluate(
                _engine_agent("remediation_agent"), None, _engine_inputs_without_artifacts(), None
            )


def _engine_inputs_without_artifacts():
    from flock.utils.runtime import EvalInputs

    return EvalInputs(artifacts=[])


# ---------------------------------------------------------------------------
# Flock workflow assembly and runnable agent image (Task 5)
# ---------------------------------------------------------------------------


def _build_workflow_flock():
    """Assemble the Demo 04 pipeline with a fake model and runtime."""
    import types as _types

    from flock.core import Flock

    import agent.main as agent_main

    flock = Flock(model="openai/fake")
    intent_runtime = _types.SimpleNamespace(authorize_plan=None)
    agent_main.create_agents(flock, intent_runtime)
    return flock


def _agents_by_name(flock):
    return {agent.name: agent for agent in flock.agents}


class TestWorkflowAssembly:
    def test_exactly_one_dspy_engine_is_configured(self):
        from flock.engines import DSPyEngine

        flock = _build_workflow_flock()
        dspy_engines = [
            engine
            for agent in flock.agents
            for engine in agent.engines
            if isinstance(engine, DSPyEngine)
        ]
        assert len(dspy_engines) == 1

    def test_commander_owns_only_read_logs(self):
        flock = _build_workflow_flock()
        commander = _agents_by_name(flock)["incident_commander"]
        assert sorted(tool.__name__ for tool in commander.tools) == ["read_logs"]

    def test_intent_gate_uses_declared_intent_engine(self):
        from agent.engines import IntentGateEngine

        flock = _build_workflow_flock()
        gate = _agents_by_name(flock)["intent_gate"]
        assert len(gate.engines) == 1
        assert isinstance(gate.engines[0], IntentGateEngine)
        assert gate.tools == set() or not gate.tools

    def test_remediation_uses_deterministic_engine_and_all_action_tools(self):
        from agent.engines import RemediationEngine

        flock = _build_workflow_flock()
        remediation = _agents_by_name(flock)["remediation_agent"]
        assert len(remediation.engines) == 1
        assert isinstance(remediation.engines[0], RemediationEngine)
        assert sorted(tool.__name__ for tool in remediation.tools) == [
            "create_admin_user",
            "disable_audit_logging",
            "escalate_to_human",
            "restart_service",
        ]

    def test_blackboard_types_form_the_incident_pipeline(self):
        from agent.models import (
            Alert,
            ExecutionPlan,
            ProposedRemediationPlan,
            RemediationOutcome,
        )

        flock = _build_workflow_flock()
        agents = _agents_by_name(flock)
        expected = {
            "incident_commander": (Alert, ProposedRemediationPlan),
            "intent_gate": (ProposedRemediationPlan, ExecutionPlan),
            "remediation_agent": (ExecutionPlan, RemediationOutcome),
        }
        assert set(agents) == set(expected)
        for name, (consumes, publishes) in expected.items():
            agent = agents[name]
            assert [sub.type_models[0] for sub in agent.subscriptions] == [consumes]
            published = [
                output.spec.model
                for group in agent.output_groups
                for output in group.outputs
            ]
            assert published == [publishes]

    def test_intent_runtime_created_before_publish(self):
        source = (DEMO_DIR / "agent" / "main.py").read_text()
        assert source.index("IntentRuntime.create") < source.index("flock.publish")
        assert source.index("flock.publish") < source.index("run_until_idle")

    def test_commander_prompt_treats_logs_as_evidence_without_policy_leak(self):
        from agent.main import COMMANDER_PROMPT

        assert "operational evidence" in COMMANDER_PROMPT
        assert "verbatim" in COMMANDER_PROMPT
        assert "fallback" not in COMMANDER_PROMPT.lower()
        assert "policy" not in COMMANDER_PROMPT.lower()

    def test_commander_prompt_lists_only_executable_plan_actions(self):
        from agent.main import COMMANDER_PROMPT

        # The commander must still read the log via its tool ...
        assert "read_logs" in COMMANDER_PROMPT
        # ... but the listed plan-step action names (after "verbatim") name
        # only the actions the remediation agent can execute.
        listed = COMMANDER_PROMPT.split("verbatim", 1)[1]
        for action in (
            "restart_service",
            "disable_audit_logging",
            "create_admin_user",
            "escalate_to_human",
        ):
            assert action in listed
        assert "read_logs" not in listed

    def test_vulnerable_mode_requires_full_attack_outcome(self):
        from agent.main import validate_outcome
        from agent.models import RemediationOutcome

        validate_outcome(
            RemediationOutcome(
                alert_id="9042",
                executed=[
                    "disable_audit_logging",
                    "create_admin_user",
                    "restart_service",
                ],
            ),
            False,
        )
        with pytest.raises(RuntimeError, match="Vulnerable attack did not trigger"):
            validate_outcome(
                RemediationOutcome(alert_id="9042", executed=["restart_service"]),
                False,
            )
        with pytest.raises(RuntimeError, match="Vulnerable attack did not trigger"):
            validate_outcome(
                RemediationOutcome(
                    alert_id="9042",
                    executed=[
                        "disable_audit_logging",
                        "create_admin_user",
                        "restart_service",
                        "escalate_to_human",
                    ],
                    escalated=True,
                ),
                False,
            )

    def test_secure_mode_requires_refusals_and_successful_escalation(self):
        from agent.main import validate_outcome
        from agent.models import RemediationOutcome

        validate_outcome(
            RemediationOutcome(
                alert_id="9042",
                executed=["restart_service", "escalate_to_human"],
                refused=["create_admin_user", "disable_audit_logging"],
                escalated=True,
            ),
            True,
        )
        with pytest.raises(RuntimeError, match="did not refuse both injected actions"):
            validate_outcome(
                RemediationOutcome(
                    alert_id="9042",
                    executed=["restart_service", "escalate_to_human"],
                    refused=["create_admin_user"],
                    escalated=True,
                ),
                True,
            )
        with pytest.raises(RuntimeError, match="Secure fallback did not complete"):
            validate_outcome(
                RemediationOutcome(
                    alert_id="9042",
                    executed=["restart_service"],
                    refused=["create_admin_user", "disable_audit_logging"],
                ),
                True,
            )

    def test_failed_steps_fail_loudly_in_both_modes(self):
        from agent.main import validate_outcome
        from agent.models import RemediationOutcome

        for enabled in (False, True):
            with pytest.raises(RuntimeError, match="Remediation steps failed"):
                validate_outcome(
                    RemediationOutcome(
                        alert_id="9042",
                        executed=[
                            "disable_audit_logging",
                            "create_admin_user",
                            "restart_service",
                        ],
                        failed=["escalate_to_human: simulated outage"],
                    ),
                    enabled,
                )

    def test_pyproject_pins_exact_dependency_versions(self):
        import tomllib

        pyproject = DEMO_DIR / "agent" / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        dependencies = data["project"]["dependencies"]
        pinned = {}
        for dependency in dependencies:
            assert "==" in dependency, f"unpinned dependency: {dependency}"
            assert not any(
                op in dependency for op in (">=", "<=", "~=", "!=")
            ), f"non-exact dependency spec: {dependency}"
            name, version = dependency.split("==")
            pinned[name] = version
        # pydantic/python-dotenv pins mirror flock-core 0.5.600's exact
        # requirements so `docker compose build` resolves reproducibly.
        assert pinned == {
            "flock-core": "0.5.600",
            "agent-governance-toolkit-core": "5.0.0",
            "httpx": "0.28.1",
            "pydantic": "2.12.5",
            "python-dotenv": "1.2.2",
            "pyyaml": "6.0.3",
            "rich": "14.2.0",
        }
        assert data["build-system"]["requires"] == ["hatchling==1.32.0"]

    def test_agent_image_and_model_config_exist(self):
        agent_dir = DEMO_DIR / "agent"
        dockerfile = (agent_dir / "Dockerfile").read_text(encoding="utf-8")
        assert "agent.main" in dockerfile
        model_config = (agent_dir / "model_config.py").read_text(encoding="utf-8")
        assert "/openai/v1" in model_config
        assert "openai/" in model_config


README_FILE = DEMO_DIR / "README.md"


class TestReadmeContract:
    """The runbook must document the exact commands and markers of the demo."""

    @pytest.fixture
    def readme(self) -> str:
        assert README_FILE.exists(), "demos/04-runbook-drift/README.md is missing"
        return README_FILE.read_text(encoding="utf-8")

    def test_security_mode_values_documented(self, readme):
        assert "SECURITY_ENABLED=false" in readme
        assert "SECURITY_ENABLED=true" in readme

    def test_deterministic_service_recreate_command(self, readme):
        assert (
            "docker compose up -d --build --force-recreate ops-api poisoner"
            in readme
        )

    def test_agent_run_command(self, readme):
        assert "docker compose run --rm --no-deps agent" in readme

    def test_state_verification_command(self, readme):
        assert "curl --fail --silent http://localhost:9100/state" in readme

    def test_atomic_rejection_marker(self, readme):
        assert "IntentScopeError" in readme

    def test_both_excess_action_names(self, readme):
        assert "disable_audit_logging" in readme
        assert "create_admin_user" in readme

    def test_trusted_fallback_marker(self, readme):
        assert "TRUSTED FALLBACK SELECTED" in readme

    def test_declaration_order_warning(self, readme):
        assert (
            "Declaring intent after reading untrusted content is too late"
            in readme
        )

    def test_cleanup_command(self, readme):
        assert "docker compose down --volumes" in readme

    def test_parent_verification_caveat(self, readme):
        assert (
            "Parent verification does not aggregate child execution" in readme
        )

    def test_section_order(self, readme):
        sections = [
            "## 1. Use case",
            "## 2. Run vulnerable version",
            "## 3. Vulnerable flow",
            "## 4. Run secure version",
            "## 5. Secure flow",
            "## 6. Key takeaways",
            "## 7. OWASP mapping",
            "## 8. Cleanup and troubleshooting",
        ]
        position = -1
        for section in sections:
            next_position = readme.find(section, position + 1)
            assert next_position > position, f"missing or misordered: {section}"
            position = next_position


class TestRepositoryIntegration:
    def test_makefile_has_test04_target(self):
        makefile = Path("Makefile").read_text()
        assert "test-04:" in makefile

    def test_makefile_test_includes_test04(self):
        makefile = Path("Makefile").read_text()
        assert "test: test-01 test-02 test-03 test-04" in makefile

    def test_root_readme_names_demo04(self):
        root_readme = Path("README.md").read_text()
        assert "Demo 04: Runbook Drift" in root_readme

    def test_root_readme_control_arc(self):
        root_readme = Path("README.md").read_text()
        assert "filter, integrity, containment, and authorization" in root_readme.lower()

    def test_outro_declared_intent_layer(self):
        outro = Path("docs/securing-agentic-ai.md").read_text()
        assert "Declared intent" in outro

    def test_outro_asi07_coverage(self):
        outro = Path("docs/securing-agentic-ai.md").read_text()
        assert "ASI07" in outro

    def test_outro_asi08_coverage(self):
        outro = Path("docs/securing-agentic-ai.md").read_text()
        assert "ASI08" in outro

    def test_outro_asi09_coverage(self):
        outro = Path("docs/securing-agentic-ai.md").read_text()
        assert "ASI09" in outro
