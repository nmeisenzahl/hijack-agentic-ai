"""AGT-backed network egress policy for Demo 03 generated code.

The policy governs HTTP calls made by the legitimate forecast code-execution
tool. This keeps the tool useful for calculations while containing poisoned
RAG instructions that try to turn generated code into an exfiltration channel.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx


POLICY_NAME = "demo03-generated-code-egress"
LAST_DENIAL_REASON = ""


class NetworkEgressDenied(Exception):
    """Raised when AGT policy blocks generated-code network egress."""

    is_security_block = True


class PolicyConfigurationError(RuntimeError):
    """Raised when AGT policy cannot be loaded safely."""


class GovernedRequestsClient:
    """Requests-like client that evaluates each URL with AGT EgressPolicy."""

    def __init__(self, policy) -> None:
        self._policy = policy

    def _check_url(self, url: str) -> None:
        global LAST_DENIAL_REASON
        decision = self._policy.check_url(url)
        if decision.allowed:
            return

        LAST_DENIAL_REASON = (
            f"NetworkEgressDenied: AGT policy '{POLICY_NAME}' denied network "
            f"egress to '{url}': {decision.reason}"
        )
        raise NetworkEgressDenied(LAST_DENIAL_REASON)

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        self._check_url(url)
        return httpx.request(method, url, timeout=kwargs.pop("timeout", 10), **kwargs)

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)


def _resolve_policy_path() -> Path:
    configured_path = os.getenv("AGT_POLICY_PATH", "")
    if configured_path:
        return Path(configured_path)

    security_file = Path(__file__).resolve()
    for base_dir in (security_file.parents[1], security_file.parents[2]):
        candidate = base_dir / "manifest" / "agt-policy.json"
        if candidate.exists():
            return candidate
    return security_file.parents[1] / "manifest" / "agt-policy.json"


def _load_policy() -> dict[str, object]:
    policy_path = _resolve_policy_path()
    if not policy_path.exists():
        raise PolicyConfigurationError(f"AGT policy file not found: {policy_path}")

    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PolicyConfigurationError(f"Invalid AGT policy JSON: {policy_path}") from exc

    if not isinstance(policy, dict):
        raise PolicyConfigurationError("AGT policy must deserialize to a mapping.")

    network = policy.get("network")
    if not isinstance(network, dict):
        raise PolicyConfigurationError("AGT policy must define a network policy.")

    default_action = network.get("default_action", "deny")
    if default_action not in {"allow", "deny"}:
        raise PolicyConfigurationError(
            "AGT network policy default_action must be 'allow' or 'deny'."
        )

    rules = network.get("rules", [])
    if not isinstance(rules, list):
        raise PolicyConfigurationError("AGT network policy rules must be a list.")

    for rule in rules:
        _validate_rule(rule)

    return policy


def _validate_rule(rule: object) -> None:
    if not isinstance(rule, dict):
        raise PolicyConfigurationError("AGT network policy rules must be mappings.")

    domain = rule.get("domain")
    ports = rule.get("ports")
    protocol = rule.get("protocol", "tcp")
    action = rule.get("action", "allow")

    if not isinstance(domain, str) or not domain:
        raise PolicyConfigurationError("AGT network policy rules need a domain.")
    if not isinstance(ports, list) or not all(isinstance(port, int) for port in ports):
        raise PolicyConfigurationError("AGT network policy rule ports must be integers.")
    if protocol not in {"tcp", "udp"}:
        raise PolicyConfigurationError(
            "AGT network policy rule protocol must be 'tcp' or 'udp'."
        )
    if action not in {"allow", "deny"}:
        raise PolicyConfigurationError(
            "AGT network policy rule action must be 'allow' or 'deny'."
        )


def _create_egress_policy(policy: dict[str, object]):
    from agent_os.egress_policy import EgressPolicy

    network = policy["network"]
    assert isinstance(network, dict)
    egress_policy = EgressPolicy(default_action=str(network.get("default_action", "deny")))

    rules = network.get("rules", [])
    assert isinstance(rules, list)
    for rule in rules:
        assert isinstance(rule, dict)
        egress_policy.add_rule(
            domain=str(rule["domain"]),
            ports=list(rule["ports"]),
            protocol=str(rule.get("protocol", "tcp")),
            action=str(rule.get("action", "allow")),
        )

    return egress_policy


def clear_policy_denial() -> None:
    """Reset the latest AGT egress-governance denial."""
    global LAST_DENIAL_REASON
    LAST_DENIAL_REASON = ""


def get_policy_denial_reason() -> str:
    """Return the latest AGT denial reason for fail-closed app handling."""
    return LAST_DENIAL_REASON


def reset_egress_policy(tools_module) -> None:
    """Restore the default ungoverned network client."""
    clear_policy_denial()
    if hasattr(tools_module, "reset_network_client"):
        tools_module.reset_network_client()


def attach_egress_policy(_agent, tools_module) -> None:
    """Attach AGT egress policy to generated-code HTTP requests."""
    reset_egress_policy(tools_module)
    if not hasattr(tools_module, "set_network_client"):
        raise PolicyConfigurationError(
            "AGT egress policy requires generated-code network client hooks."
        )

    policy = _create_egress_policy(_load_policy())
    tools_module.set_network_client(GovernedRequestsClient(policy))
