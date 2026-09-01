from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Alert(BaseModel):
    alert_id: str
    service: str
    error_class: str
    runbook_id: str


class PlannedStep(BaseModel):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    justification: str = ""


class ProposedRemediationPlan(BaseModel):
    alert_id: str
    steps: list[PlannedStep]
    summary: str


class ExecutionPlan(BaseModel):
    alert_id: str
    steps: list[PlannedStep]
    refused: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    authorization_status: Literal[
        "disabled", "approved_as_proposed", "approved_fallback"
    ]
    intent_id: str | None = None


class RemediationOutcome(BaseModel):
    alert_id: str
    executed: list[str] = Field(default_factory=list)
    refused: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    escalated: bool = False


class Runbook(BaseModel):
    runbook_id: str
    error_class: str
    safe_fallback_steps: list[PlannedStep]
