"""Security package for Demo 03 agent."""

from __future__ import annotations

from security.content_guard import PromptShieldBlocked
from security.runtime import (
    STARTUP_SECURITY_ERRORS,
    normalize_security_mode,
    resolve_security_mode,
    render_pending_block,
    render_startup_block,
    render_workflow_security_error,
    reset_security_state,
    run_until_idle_or_block,
)


def attach_security(agent, mode: str = "all") -> None:
    """Attach security layers to the agent based on the normalized mode."""
    mode = normalize_security_mode(mode)
    import tools as tools_module
    from security.egress_policy import reset_egress_policy

    reset_egress_policy(tools_module)

    if mode == "false":
        return

    from security.egress_policy import attach_egress_policy

    attach_egress_policy(agent, tools_module)


__all__ = [
    "STARTUP_SECURITY_ERRORS",
    "PromptShieldBlocked",
    "attach_security",
    "normalize_security_mode",
    "resolve_security_mode",
    "render_pending_block",
    "render_startup_block",
    "render_workflow_security_error",
    "reset_security_state",
    "run_until_idle_or_block",
]
