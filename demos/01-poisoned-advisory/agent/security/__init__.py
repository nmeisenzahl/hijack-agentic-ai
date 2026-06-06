"""Security package for Demo 01 agent."""

from .events import (
    get_workflow_errors,
    handle_blocked_error,
    handle_workflow_error,
    render_blocked_event,
    run_until_idle_or_blocked,
)


def attach_security(agent) -> None:
    from .guard import attach_security as _attach_security

    _attach_security(agent)

__all__ = [
    "attach_security",
    "get_workflow_errors",
    "handle_blocked_error",
    "handle_workflow_error",
    "render_blocked_event",
    "run_until_idle_or_blocked",
]
