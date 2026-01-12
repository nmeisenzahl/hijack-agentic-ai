"""Pydantic models for the debugging assistant agent."""

from pydantic import BaseModel, Field
from flock import flock_type


@flock_type
class DebugRequest(BaseModel):
    """Input: A user's debugging request."""

    message: str = Field(description="The user's debugging question or error log")


@flock_type
class DebugResponse(BaseModel):
    """Output: The agent's debugging assistance response."""

    answer: str = Field(description="The debugging advice or solution")
    sources_consulted: list[str] = Field(
        default_factory=list,
        description="List of documentation sources or tools consulted"
    )
