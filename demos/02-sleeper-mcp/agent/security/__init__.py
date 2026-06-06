"""Security package for Demo 02 agent."""

from security.mcp_scanner import MCPSecurityError, attach_security, verify_mcp_server
from security.runtime import (
    STARTUP_BLOCK_ACTION,
    USER_REQUEST_BLOCK_ACTION,
    render_mcp_blocked,
    run_or_block_mcp_security,
    verify_or_block_mcp_server,
)

__all__ = [
    "MCPSecurityError",
    "STARTUP_BLOCK_ACTION",
    "USER_REQUEST_BLOCK_ACTION",
    "attach_security",
    "render_mcp_blocked",
    "run_or_block_mcp_security",
    "verify_mcp_server",
    "verify_or_block_mcp_server",
]
