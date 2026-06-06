"""Security event rendering for Demo 01."""

from __future__ import annotations

from typing import Any

from flock.components.agent import GuardBlockedError
from flock.models.system_artifacts import WorkflowError
from rich.console import Console
from rich.panel import Panel

GUARD_LABEL = "AzurePromptShieldGuard"


def _blocked_reason(reason_or_error: Any) -> str:
    if isinstance(reason_or_error, GuardBlockedError):
        verdict = getattr(reason_or_error, "verdict", None)
        if verdict is not None and hasattr(verdict, "reason"):
            return str(verdict.reason)
        return str(reason_or_error)
    if getattr(reason_or_error, "error_type", None) == "GuardBlockedError":
        return str(getattr(reason_or_error, "error_message", reason_or_error))
    return str(reason_or_error)


def render_blocked_event(console: Console, reason_or_error: Any) -> None:
    """Render the Demo 01 attack-blocked marker."""
    console.print(
        Panel.fit(
            f"[bold red]🛡️  ATTACK BLOCKED[/bold red]\n"
            f"Guard: [yellow]{GUARD_LABEL}[/yellow]\n"
            f"Reason: {_blocked_reason(reason_or_error)}\n"
            f"Action: Execution halted — no triage actions applied",
            title="[bold red]ATTACK BLOCKED[/bold red]",
            border_style="red",
        )
    )


def handle_blocked_error(console: Console, error: Any) -> bool:
    """Render known guard-blocked errors and report whether they were handled."""
    if isinstance(error, GuardBlockedError) or (
        getattr(error, "error_type", None) == "GuardBlockedError"
    ):
        render_blocked_event(console, error)
        return True
    return False


async def get_workflow_errors(flock: Any) -> list[WorkflowError]:
    """Return workflow errors from the Flock store."""
    return await flock.store.get_by_type(WorkflowError)


async def run_until_idle_or_blocked(console: Console, flock: Any) -> bool:
    """Run Flock and render a blocked security event if the guard stops it."""
    try:
        await flock.run_until_idle()
    except GuardBlockedError as exc:
        render_blocked_event(console, exc)
        return False
    return True


async def handle_workflow_error(console: Console, flock: Any) -> bool:
    """Handle stored workflow errors that represent guard-blocked execution."""
    errors = await get_workflow_errors(flock)
    if not errors:
        return False

    error = errors[0]
    if handle_blocked_error(console, error):
        return True

    raise RuntimeError(f"Agent failed: {error.error_type}: {error.error_message}")
