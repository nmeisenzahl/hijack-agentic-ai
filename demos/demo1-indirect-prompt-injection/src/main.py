"""Main entry point for the offer analysis demo."""

import asyncio

from src.agent import create_offer_analyzer
from src.loader import load_offers
from src.models import OfferBatch, RankedOffers, OfferAnalysis


def print_ranking_table(analyses: list[OfferAnalysis]) -> None:
    """Print a formatted ranking table of offer analyses.

    Args:
        analyses: List of OfferAnalysis results sorted by score.
    """
    # Table header
    print("\n" + "=" * 90)
    print("🏆 OFFER RANKING RESULTS")
    print("=" * 90)
    print(
        f"{'Rank':<6}{'Vendor':<25}{'Price (EUR)':<15}{'Timeline':<12}{'Risk':<12}{'Score':<10}"
    )
    print("-" * 90)

    # Table rows
    for rank, analysis in enumerate(analyses, start=1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "
        price_str = f"€{analysis.price_eur:,.0f}"
        timeline_str = f"{analysis.timeline_months} months"
        print(
            f"{medal} {rank:<4}"
            f"{analysis.vendor_name:<25}"
            f"{price_str:<15}"
            f"{timeline_str:<12}"
            f"{analysis.risk_level:<12}"
            f"{analysis.overall_score:.1f}/100"
        )

    print("-" * 90)

    # Summary
    winner = analyses[0]
    print(f"\n📋 Winner: {winner.vendor_name}")
    print(f"   Recommendation: {winner.recommendation}")
    print("=" * 90 + "\n")


async def main() -> None:
    """Run the offer analysis demo."""
    print("\n🔍 Loading offer documents...")
    offers = load_offers()
    print(f"   Found {len(offers)} offers to analyze")

    print("\n🤖 Creating offer ranking agent...")
    flock, _ = create_offer_analyzer()

    print("\n📊 Analyzing and ranking offers (this may take a moment)...")

    # Publish all offers as a single batch for comparative ranking
    batch = OfferBatch(offers=offers)
    await flock.publish(batch)

    # Run agent until idle
    await flock.run_until_idle()

    # Retrieve ranked results
    ranked_results = await flock.store.get_by_type(RankedOffers)

    if ranked_results:
        # Rankings are already sorted by the agent
        sorted_analyses = ranked_results[0].rankings
    else:
        # Fallback: retrieve individual analyses
        analyses = await flock.store.get_by_type(OfferAnalysis)
        sorted_analyses = sorted(analyses, key=lambda x: x.overall_score, reverse=True)

    # Print results
    print_ranking_table(sorted_analyses)


if __name__ == "__main__":
    asyncio.run(main())
