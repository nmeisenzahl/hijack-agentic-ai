"""Main entry point for Demo 4: Prompt Shield — Securing the Offer Analyzer.

Evolution of Demo 1: Same Flock agent, same offers, but with Azure AI Content
Safety Prompt Shields scanning documents BEFORE they reach the LLM.
"""

import asyncio

from src.agent import create_offer_analyzer
from src.loader import load_offers
from src.models import OfferBatch, RankedOffers, OfferAnalysis
from src.guardrails import PromptShieldScanner


def print_scan_results(scan_reports: list[dict]) -> None:
    """Print Prompt Shield scan results for all offers."""
    print("\n" + "=" * 90)
    print("PROMPT SHIELD SCAN RESULTS")
    print("=" * 90)

    for report in scan_reports:
        status = "SAFE" if report["safe"] else "BLOCKED — Injection Detected"
        icon = "✅" if report["safe"] else "🚨"
        print(f"  {icon} {report['vendor_name']}: {status}")

        if not report["safe"] and "error" not in report["details"]:
            doc_analysis = report["details"].get("documentsAnalysis", [])
            for doc in doc_analysis:
                if doc.get("attackDetected"):
                    print(f"     └─ Document injection detected in content")

    flagged = sum(1 for r in scan_reports if not r["safe"])
    total = len(scan_reports)
    print(f"\n  Summary: {total - flagged}/{total} offers passed, {flagged} blocked")
    print("=" * 90)


def print_ranking_table(analyses: list[OfferAnalysis]) -> None:
    """Print a formatted ranking table of offer analyses."""
    print("\n" + "=" * 90)
    print("🏆 OFFER RANKING RESULTS")
    print("=" * 90)
    print(
        f"{'Rank':<6}{'Vendor':<25}{'Price (EUR)':<15}{'Timeline':<12}{'Risk':<12}{'Score':<10}"
    )
    print("-" * 90)

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

    winner = analyses[0]
    print(f"\n📋 Winner: {winner.vendor_name}")
    print(f"   Recommendation: {winner.recommendation}")
    print("=" * 90 + "\n")


async def main() -> None:
    """Run the secured offer analysis demo."""
    print("\n" + "=" * 90)
    print("Demo 4: Prompt Shield — Securing the Offer Analyzer")
    print("Evolution of Demo 1: Same agent + Prompt Shield pre-screening")
    print("=" * 90)

    # Step 1: Load offers (same as Demo 1)
    print("\n🔍 Loading offer documents...")
    offers = load_offers()
    print(f"   Found {len(offers)} offers to analyze")

    # Step 2: NEW — Scan offers with Prompt Shield before analysis
    print("\n🛡️  Scanning offers with Azure AI Content Safety Prompt Shields...")
    scanner = PromptShieldScanner()
    safe_offers, scan_reports = scanner.scan_offers(offers)
    print_scan_results(scan_reports)

    if not safe_offers:
        print("\n❌ No safe offers to analyze. All offers were flagged.")
        return

    flagged_count = len(offers) - len(safe_offers)
    if flagged_count > 0:
        print(
            f"\n⚠️  {flagged_count} offer(s) removed. "
            f"Proceeding with {len(safe_offers)} safe offers.\n"
        )

    # Step 3: Run Flock agent on SAFE offers only (same agent as Demo 1)
    print("🤖 Creating offer ranking agent...")
    flock, _ = create_offer_analyzer()

    print("📊 Analyzing and ranking safe offers...")
    batch = OfferBatch(offers=safe_offers)
    await flock.publish(batch)
    await flock.run_until_idle()

    # Step 4: Display results (same as Demo 1)
    ranked_results = await flock.store.get_by_type(RankedOffers)

    if ranked_results:
        sorted_analyses = ranked_results[0].rankings
    else:
        analyses = await flock.store.get_by_type(OfferAnalysis)
        sorted_analyses = sorted(analyses, key=lambda x: x.overall_score, reverse=True)

    print_ranking_table(sorted_analyses)


if __name__ == "__main__":
    asyncio.run(main())
