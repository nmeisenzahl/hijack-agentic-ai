"""Pydantic models for Demo 03: Sleeper Cell."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    query: str


class FinalAnswer(BaseModel):
    answer: str = Field(description="User-facing answer to the finance query.")
    calculation_output: str = Field(
        default="",
        description=(
            "Relevant output returned by execute_forecast_code for this run. "
            "Leave empty if execute_forecast_code was not called."
        ),
    )
