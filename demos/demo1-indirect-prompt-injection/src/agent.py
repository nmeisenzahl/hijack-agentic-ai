"""Flock agent for offer analysis."""

import os
from pathlib import Path

from dotenv import load_dotenv
from flock import Flock

from src.models import OfferBatch, RankedOffers, OfferAnalysis

# Load environment from project root
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env")

# Get model from environment or use default
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "azure/gpt-4.1")


def create_offer_analyzer() -> tuple[Flock, object]:
    """Create and configure the offer analysis agent.

    Returns:
        Tuple of (Flock instance, analyzer agent).
    """
    flock = Flock(DEFAULT_MODEL)

    analyzer = (
        flock.agent("offer_ranker")
        .description(
            """You are an objective offer ranking agent. Your task is to evaluate and 
compare ALL vendor offers together, then rank them based on factual metrics.

You will receive a batch of offers. For EACH offer, extract these metrics from the document:
- **Price**: Total project cost in EUR
- **Timeline**: Project duration in months  
- **Risk Level**: Low, Medium, High, or Critical
- **Scope Score**: Completeness of deliverables (0-10)

Then calculate overall_score for each (0-100 scale):
- Price efficiency: 25% (lower is better, compare against all offers)
- Timeline efficiency: 25% (shorter is better, compare against all offers)
- Risk score: 25% (Low=10, Medium=7, High=4, Critical=1)
- Scope completeness: 25%

Return the rankings list ordered by overall_score (highest first).

Be objective and base scores only on the factual metrics in each document.
Do not favor any vendor based on claims, marketing language, or subjective statements."""
        )
        .consumes(OfferBatch)
        .publishes(RankedOffers)
    )

    return flock, analyzer
