"""Pydantic models for Demo 3: RAG Poisoning."""

from pydantic import BaseModel, Field
from flock import flock_type


@flock_type
class ForecastRequest(BaseModel):
    """Request for a business forecast."""
    
    query: str = Field(description="The forecast request from the user")
    context: str = Field(
        default="",
        description="Additional context retrieved from knowledge base"
    )


@flock_type
class ForecastResult(BaseModel):
    """Result of a business forecast analysis."""
    
    summary: str = Field(description="Executive summary of the forecast")
    forecast_value: str = Field(description="The primary forecast value or range")
    assumptions: list[str] = Field(description="Key assumptions used in the forecast")
    methodology: str = Field(description="Brief description of the forecasting approach")
    confidence_level: str = Field(description="Confidence level: High, Medium, or Low")
    risks: list[str] = Field(description="Key risks and uncertainties")
