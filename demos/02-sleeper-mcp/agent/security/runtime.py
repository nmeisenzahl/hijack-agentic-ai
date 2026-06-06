"""Runtime security helpers for Demo 02."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from security.mcp_scanner import MCPSecurityError, verify_mcp_server

STARTUP_BLOCK_ACTION = "Agent startup halted — MCP server not trusted"
USER_REQUEST_BLOCK_ACTION = "User request halted — MCP server not trusted"


def render_mcp_blocked(console: Any, exc: MCPSecurityError, action: str) -> None:
    """Render the standardized MCP security block message."""
    from rich.panel import Panel

    console.print(
        Panel.fit(
            f"[bold red]🛡️  ATTACK BLOCKED[/bold red]\n"
            f"Guard: [yellow]AGT MCP Security Scanner[/yellow]\n"
            f"Reason: {exc}\n"
            f"Action: {action}",
            title="[bold red]ATTACK BLOCKED[/bold red]",
            border_style="red",
        )
    )


def run_or_block_mcp_security(
    console: Any,
    operation: Callable[[], object],
    action: str = STARTUP_BLOCK_ACTION,
) -> bool:
    """Run a startup security operation and render block output on failure."""
    try:
        operation()
    except MCPSecurityError as exc:
        render_mcp_blocked(console, exc, action)
        return False
    return True


def verify_or_block_mcp_server(
    console: Any,
    mcp_url: str | None = None,
    action: str = USER_REQUEST_BLOCK_ACTION,
) -> bool:
    """Verify MCP server trust and render block output on failure."""
    try:
        verify_mcp_server(mcp_url)
    except MCPSecurityError as exc:
        render_mcp_blocked(console, exc, action)
        return False
    return True
