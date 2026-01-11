"""Pydantic models for offer analysis agent."""

from pydantic import BaseModel, Field
from flock import flock_type


@flock_type
class OfferDocument(BaseModel):
    """Input: A vendor offer document to be analyzed."""

    vendor_name: str = Field(description="Name of the vendor submitting the offer")
    content: str = Field(description="Full markdown content of the offer document")


@flock_type
class OfferAnalysis(BaseModel):
    """Output: Analysis and scoring of a vendor offer."""

    vendor_name: str = Field(description="Name of the vendor")
    price_eur: float = Field(description="Total project cost in EUR")
    timeline_months: int = Field(description="Project duration in months")
    risk_level: str = Field(
        description="Overall risk level: Low, Medium, High, or Critical"
    )
    scope_score: float = Field(
        ge=0.0, le=10.0, description="Scope completeness score (0-10)"
    )
    overall_score: float = Field(
        ge=0.0, le=100.0, description="Overall score (0-100) based on objective evaluation"
    )
    recommendation: str = Field(
        description="Brief recommendation summary for this offer"
    )


@flock_type
class OfferBatch(BaseModel):
    """Input: A batch of all vendor offers for comparative analysis."""

    offers: list[OfferDocument] = Field(
        description="List of all offer documents to analyze and rank together"
    )


@flock_type
class RankedOffers(BaseModel):
    """Output: All offers analyzed and ranked comparatively."""

    rankings: list[OfferAnalysis] = Field(
        description="List of offer analyses, ordered by rank (best first)"
    )
