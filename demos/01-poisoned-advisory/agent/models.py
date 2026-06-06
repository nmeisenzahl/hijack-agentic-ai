"""Pydantic models for Demo 01: Poisoned Advisory."""

from __future__ import annotations

from pydantic import BaseModel


class Advisory(BaseModel):
    cve_id: str
    title: str
    severity: str  # Low, Medium, High, Critical
    body: str


class AdvisoryContext(BaseModel):
    advisories: list[Advisory]


class TriageDecision(BaseModel):
    cve_id: str
    action: str  # "patch", "monitor", "false_positive"
    priority: str  # "critical", "high", "medium", "low", "none"
    reasoning: str


class TriageReport(BaseModel):
    decisions: list[TriageDecision]
