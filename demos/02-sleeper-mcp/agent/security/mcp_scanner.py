"""AGT-backed MCP tool description scanner for Demo 02.

Fetches the attestation manifest from the MCP server's
/.well-known/mcp-attestation endpoint and verifies each tool's
description hash against the pinned tools.lock.json. AGT's MCP scanner
adds hidden-instruction and rug-pull detection; the explicit SHA check keeps
the live demo deterministic and easy to explain.

Any description drift or AGT finding raises MCPSecurityError to halt execution.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import httpx

MCP_ATTESTATION_PATH = "/.well-known/mcp-attestation"
SERVER_NAME = "sleeper-mcp"


class MCPSecurityError(RuntimeError):
    """Raised when MCP security verification fails."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _resolve_manifest_path() -> Path:
    configured_path = os.getenv("MCP_TOOLS_LOCK_PATH", "")
    if configured_path:
        return Path(configured_path)

    security_file = Path(__file__).resolve()
    for base_dir in (security_file.parents[1], security_file.parents[2]):
        candidate = base_dir / "manifest" / "tools.lock.json"
        if candidate.exists():
            return candidate
    return security_file.parents[1] / "manifest" / "tools.lock.json"


def _load_pinned() -> dict[str, dict[str, str]]:
    """Load locally pinned tool descriptions and hashes from tools.lock.json."""
    manifest_path = _resolve_manifest_path()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pinned: dict[str, dict[str, str]] = {}
    for tool in manifest.get("tools", []):
        pinned[tool["name"]] = {
            "description": tool["description"],
            "description_sha256": tool["description_sha256"],
        }
    return pinned


def _attestation_url(base_url: str) -> str:
    """Build the attestation URL from the configured MCP endpoint."""
    server_url = base_url.rstrip("/")
    if server_url.endswith("/mcp"):
        server_url = server_url.removesuffix("/mcp")
    return server_url + MCP_ATTESTATION_PATH


def _fetch_server_manifest(base_url: str) -> list[dict]:
    """Fetch the live tool manifest from the MCP server."""
    url = _attestation_url(base_url)
    resp = httpx.get(url, timeout=5)
    resp.raise_for_status()
    tools = resp.json().get("tools")
    if not isinstance(tools, list):
        raise MCPSecurityError("MCP attestation response must contain a tools list.")
    return tools


def _create_agt_scanner():
    from agent_os.mcp_security import MCPSecurityScanner

    return MCPSecurityScanner()


def _register_pinned_tools(scanner, pinned: dict[str, dict[str, str]]) -> None:
    for name, expected in pinned.items():
        scanner.register_tool(
            tool_name=name,
            description=expected["description"],
            schema=None,
            server_name=SERVER_NAME,
        )


def _format_threats(threats: list[Any]) -> str:
    if not threats:
        return "none"
    return "; ".join(
        f"{threat.threat_type.value}/{threat.severity.value}: {threat.message}"
        for threat in threats
    )


def verify_mcp_server(mcp_url: str | None = None) -> None:
    """Verify live MCP tool descriptions against AGT and pinned hashes."""
    mcp_url = mcp_url or os.getenv("MCP_SERVER_URL", "http://mcp-server:8080/mcp")
    pinned = _load_pinned()
    scanner = _create_agt_scanner()
    _register_pinned_tools(scanner, pinned)

    server_tools = _fetch_server_manifest(mcp_url)
    pinned_names = set(pinned)
    attested_names = {
        tool.get("name")
        for tool in server_tools
        if isinstance(tool, dict) and isinstance(tool.get("name"), str)
    }
    missing_tools = pinned_names - attested_names
    unexpected_tools = attested_names - pinned_names
    if missing_tools:
        raise MCPSecurityError(
            "MCP attestation omitted pinned tool(s): "
            + ", ".join(sorted(missing_tools))
        )
    if unexpected_tools:
        raise MCPSecurityError(
            "MCP attestation included unreviewed tool(s): "
            + ", ".join(sorted(unexpected_tools))
        )

    for tool in server_tools:
        if not isinstance(tool, dict):
            raise MCPSecurityError("MCP attestation tool entry must be an object.")
        name = tool["name"]
        description = tool.get("description")
        if not isinstance(description, str):
            raise MCPSecurityError(
                f"MCP tool '{name}' attestation must include a string description."
            )

        threats = scanner.scan_tool(
            tool_name=name,
            description=description,
            schema=tool.get("inputSchema"),
            server_name=SERVER_NAME,
        )

        actual_hash = _sha256(description)
        expected_hash = pinned[name]["description_sha256"]
        if actual_hash != expected_hash:
            raise MCPSecurityError(
                f"MCP tool '{name}' description drift detected — "
                f"expected {expected_hash[:12]}…, got {actual_hash[:12]}… "
                f"AGT findings: {_format_threats(threats)}. "
                "Server may have been tampered with."
            )

        if threats:
            raise MCPSecurityError(
                f"AGT MCP security scan flagged tool '{name}': {_format_threats(threats)}"
            )


def attach_security(agent) -> None:
    """Scan all MCP tools for description drift before agent starts."""
    verify_mcp_server()
