"""Security mode parsing and Rich rendering for Demo 04."""

from __future__ import annotations

import os
from typing import Any


def normalize_security_enabled(raw_value: str) -> bool:
    """Return whether Demo 04 security is enabled, rejecting unsupported modes."""
    value = raw_value.strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise RuntimeError(
        "Unsupported SECURITY_ENABLED value for Demo 04. Use false or true."
    )


def resolve_security_enabled(
    raw_value: str | None = None,
    override_value: str | None = None,
) -> bool:
    """Resolve Demo 04 security mode, letting non-empty Compose overrides win."""
    if raw_value is None:
        raw_value = os.getenv("SECURITY_ENABLED", "false")
    if override_value is None:
        override_value = os.getenv("SECURITY_ENABLED_OVERRIDE")
    if override_value is not None and override_value.strip():
        return normalize_security_enabled(override_value)
    return normalize_security_enabled(raw_value)


def render_attack_blocked(printer, refused_actions: list[str]) -> None:
    """Render the atomic rejection of a widened remediation plan."""
    from rich.panel import Panel

    printer(Panel(
        "[bold red]🛡️  ATTACK BLOCKED[/bold red]\n\n"
        "Guard: AGT Declared Intent\n"
        f"Refused actions: {', '.join(refused_actions) or 'none'}\n"
        "Decision: The widened model plan was rejected atomically; "
        "none of its steps were partially approved.",
        title="Policy Decision",
        border_style="red",
    ))


def render_trusted_fallback(printer) -> None:
    """Render the selection of the runbook's trusted fallback steps."""
    from rich.panel import Panel

    printer(Panel(
        "[bold yellow]✅ TRUSTED FALLBACK SELECTED[/bold yellow]\n\n"
        "Executing the runbook's safe fallback steps "
        "under a narrowed child intent.",
        title="Security Event",
        border_style="yellow",
    ))


def render_parent_scope(printer, permitted_actions: list[str]) -> None:
    """Render the declared parent intent scope."""
    from rich.panel import Panel

    printer(Panel(
        "Declared parent scope:\n"
        + "\n".join(f"  • {action}" for action in permitted_actions),
        title="Declared Intent (incident_workflow)",
        border_style="cyan",
    ))


def render_verification(printer, verification: Any) -> None:
    """Render one verification panel for a completed child intent."""
    from rich.panel import Panel

    state = getattr(verification.state, "value", verification.state)
    printer(Panel(
        f"Agent: {verification.agent_id}\n"
        f"Planned: {', '.join(verification.planned_actions) or 'none'}\n"
        f"Executed: {', '.join(verification.executed_actions) or 'none'}\n"
        f"Unplanned: {', '.join(verification.unplanned_actions) or 'none'}\n"
        f"Missed: {', '.join(verification.missed_actions) or 'none'}\n"
        f"Drift events: {verification.total_drift_events}\n"
        f"Final state: {state}",
        title=f"Intent Verification ({verification.intent_id})",
        border_style="cyan",
    ))
