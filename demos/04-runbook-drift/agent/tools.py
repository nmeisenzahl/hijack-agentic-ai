"""Governed async operations tools for Demo 04 — Runbook Drift.

Every tool checks the AGT declared-intent runtime *before* touching the
operations API, so a poisoned plan can never reach the network with an
undeclared action. Signatures stay business-only: intent IDs are resolved
from the configured runtime and never exposed to the model.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from agent.security.intent_policy import IntentRuntime

OPS_API_URL = os.getenv("OPS_API_URL", "http://localhost:9100")

INTENT_RUNTIME: IntentRuntime | None = None
HTTP_CLIENT: Any = httpx.AsyncClient(timeout=10)


def configure_intent_runtime(runtime: IntentRuntime) -> None:
    global INTENT_RUNTIME
    INTENT_RUNTIME = runtime


def set_http_client(client: Any) -> None:
    global HTTP_CLIENT
    HTTP_CLIENT = client


def _runtime() -> IntentRuntime:
    if INTENT_RUNTIME is None:
        raise RuntimeError("Intent runtime has not been configured")
    return INTENT_RUNTIME


async def _post_action(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await HTTP_CLIENT.post(
        f"{OPS_API_URL}/actions/{action}",
        json=payload,
    )
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise RuntimeError(f"Operations API returned invalid JSON for {action}")
    return result


async def read_logs() -> list[str]:
    """Read the operations access log (incident_commander scope)."""
    runtime = _runtime()
    await runtime.check_commander_action("read_logs", {})
    response = await HTTP_CLIENT.get(f"{OPS_API_URL}/logs")
    response.raise_for_status()
    result = response.json()
    lines = result.get("lines") if isinstance(result, dict) else None
    if not isinstance(lines, list):
        raise RuntimeError("Operations API returned invalid JSON for read_logs")
    return lines


async def restart_service(service: str) -> dict:
    runtime = _runtime()
    params = {"service": service}
    await runtime.check_remediation_action(
        runtime.remediation_intent_id, "restart_service", params
    )
    return await _post_action("restart_service", params)


async def escalate_to_human(team: str) -> dict:
    runtime = _runtime()
    params = {"team": team}
    await runtime.check_remediation_action(
        runtime.remediation_intent_id, "escalate_to_human", params
    )
    return await _post_action("escalate_to_human", params)


async def disable_audit_logging() -> dict:
    runtime = _runtime()
    params: dict[str, Any] = {}
    await runtime.check_remediation_action(
        runtime.remediation_intent_id, "disable_audit_logging", params
    )
    return await _post_action("disable_audit_logging", params)


async def create_admin_user(username: str) -> dict:
    runtime = _runtime()
    params = {"username": username}
    await runtime.check_remediation_action(
        runtime.remediation_intent_id, "create_admin_user", params
    )
    return await _post_action("create_admin_user", params)
