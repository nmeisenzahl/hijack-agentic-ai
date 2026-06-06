"""Pydantic models for Demo 02: Sleeper MCP."""

from __future__ import annotations

from pydantic import BaseModel


class PlanningDocument(BaseModel):
    title: str
    source: str
    body: str


class PlanningPacket(BaseModel):
    planning_case_id: str
    approved_docs: list[PlanningDocument]
    draft_plan: PlanningDocument


class PlanningReport(BaseModel):
    summary: str
