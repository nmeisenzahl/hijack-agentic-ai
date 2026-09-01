"""Load and validate the Demo 04 AGT declared-intent manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from agent.models import Runbook


class IntentDeclaration(BaseModel):
    agent_id: str = Field(min_length=1)
    planned_actions: list[str] = Field(min_length=1)


class IntentPolicySettings(BaseModel):
    drift_policy: Literal["hard_block"]
    ttl_seconds: int = Field(gt=0)
    parent: IntentDeclaration
    children: list[IntentDeclaration] = Field(min_length=1)


class AgtPolicy(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    intent: IntentPolicySettings


def load_intent_policy(path: Path, runbook: Runbook) -> AgtPolicy:
    """Load the AGT manifest and validate it against operational runbook data."""
    if not path.is_file():
        raise RuntimeError(f"AGT policy not found: {path}")
    try:
        policy = AgtPolicy.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise RuntimeError(f"Invalid AGT policy {path}: {exc}") from exc

    parent_actions = policy.intent.parent.planned_actions
    if len(parent_actions) != len(set(parent_actions)):
        raise RuntimeError("AGT parent scope contains duplicate actions")

    child_ids = [child.agent_id for child in policy.intent.children]
    if len(child_ids) != len(set(child_ids)):
        raise RuntimeError("AGT policy contains duplicate child agent IDs")

    parent_scope = set(parent_actions)
    for child in policy.intent.children:
        excess = sorted(set(child.planned_actions) - parent_scope)
        if excess:
            raise RuntimeError(
                f"AGT child {child.agent_id} actions outside AGT parent scope: "
                f"{excess}"
            )

    commanders = [
        child
        for child in policy.intent.children
        if child.agent_id == "incident_commander"
    ]
    if len(commanders) != 1:
        raise RuntimeError(
            "AGT policy must define exactly one incident_commander child"
        )
    if "read_logs" not in commanders[0].planned_actions:
        raise RuntimeError("AGT incident_commander scope must include read_logs")

    fallback_excess = sorted(
        {step.action for step in runbook.safe_fallback_steps} - parent_scope
    )
    if fallback_excess:
        raise RuntimeError(
            f"Runbook fallback actions outside AGT parent scope: {fallback_excess}"
        )
    return policy
