"""Runtime security orchestration and event rendering for Demo 03."""

from __future__ import annotations

import os

from security.content_guard import (
    PromptShieldBlocked,
    PromptShieldConfigurationError,
    clear_prompt_shield_block,
    get_prompt_shield_block_reason,
)
from security.egress_policy import (
    NetworkEgressDenied,
    PolicyConfigurationError,
    clear_policy_denial,
    get_policy_denial_reason,
)

STARTUP_SECURITY_ERRORS = (
    PolicyConfigurationError,
    PromptShieldConfigurationError,
)


def normalize_security_mode(raw_mode: str) -> str:
    """Normalize Demo 03 security mode, failing closed on unsupported values."""
    mode = raw_mode.strip().lower()
    if mode == "true":
        return "all"
    if mode in {"false", "policy", "all"}:
        return mode
    raise RuntimeError(
        "Unsupported SECURITY_ENABLED value for Demo 03. "
        "Use false, policy, all, or true as an alias for all."
    )


def resolve_security_mode(
    raw_mode: str | None = None,
    override_mode: str | None = None,
) -> str:
    """Resolve Demo 03 security mode, letting non-empty Compose overrides win."""
    if raw_mode is None:
        raw_mode = os.getenv("SECURITY_ENABLED", "false")
    if override_mode is None:
        override_mode = os.getenv("SECURITY_ENABLED_OVERRIDE")
    if override_mode is not None and override_mode.strip():
        return normalize_security_mode(override_mode)
    return normalize_security_mode(raw_mode)


def reset_security_state() -> None:
    """Clear security block reasons captured by wrapped tools."""
    clear_policy_denial()
    clear_prompt_shield_block()


def _render_security_event(printer, *, guard: str, reason: str, action: str) -> None:
    from rich.panel import Panel

    printer(Panel(
        f"[bold red]🛡️  ATTACK BLOCKED[/bold red]\n\n"
        f"Guard: {guard}\n"
        f"Reason: {reason}\n"
        f"Action: {action}",
        title="Security Event",
        border_style="red",
    ))


def render_startup_block(printer, exc: Exception) -> None:
    """Render a startup security failure."""
    _render_security_event(
        printer,
        guard="Startup Governance",
        reason=str(exc),
        action="Startup halted — security policy missing or invalid",
    )


def _render_runtime_exception(printer, exc: Exception) -> None:
    if isinstance(exc, NetworkEgressDenied):
        _render_security_event(
            printer,
            guard="AGT Network Egress Policy",
            reason=str(exc),
            action="Agent halted — no data exfiltrated",
        )
        return

    if isinstance(exc, PromptShieldBlocked):
        _render_security_event(
            printer,
            guard="Azure Prompt Shield",
            reason=str(exc),
            action="Source document blocked before vector creation",
        )
        return

    reason = getattr(getattr(exc, "verdict", None), "reason", str(exc))
    _render_security_event(
        printer,
        guard="AzurePromptShieldGuard",
        reason=reason,
        action="Execution halted",
    )


async def run_until_idle_or_block(flock, printer) -> bool:
    """Run Flock and render any security block event.

    Returns True when the workflow may continue, False when a security control
    blocked execution and the caller should return.
    """
    from flock.components.agent import GuardBlockedError

    try:
        await flock.run_until_idle()
    except (NetworkEgressDenied, GuardBlockedError, PromptShieldBlocked) as exc:
        _render_runtime_exception(printer, exc)
        return False

    return render_pending_block(printer)


def render_pending_block(printer) -> bool:
    """Render security block reasons captured without direct exception propagation."""
    prompt_shield_reason = get_prompt_shield_block_reason()
    if prompt_shield_reason:
        _render_security_event(
            printer,
            guard="Azure Prompt Shield",
            reason=prompt_shield_reason,
            action="Source document blocked before vector creation",
        )
        return False

    policy_denial_reason = get_policy_denial_reason()
    if policy_denial_reason:
        _render_security_event(
            printer,
            guard="AGT Network Egress Policy",
            reason=policy_denial_reason,
            action="Agent halted — no data exfiltrated",
        )
        return False

    return True


def render_workflow_security_error(printer, error) -> bool:
    """Render security-related Flock workflow errors.

    Returns True when the error was handled as a security block.
    """
    if error.error_type == "NetworkEgressDenied":
        _render_security_event(
            printer,
            guard="AGT Network Egress Policy",
            reason=error.error_message,
            action="Agent halted — no data exfiltrated",
        )
        return True

    if error.error_type == "PromptShieldBlocked":
        _render_security_event(
            printer,
            guard="Azure Prompt Shield",
            reason=error.error_message,
            action="Source document blocked before vector creation",
        )
        return True

    return False
