"""Main entry point for Demo 5: Secure RAG Agent.

Evolution of Demo 3: Same Flock agent, same RAG pipeline, same documents,
but with 2-layer guardrails added for defense-in-depth.
"""

import asyncio
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from .agent import create_forecast_agent, set_rag_store, set_guardrails
from .models import ForecastRequest, ForecastResult
from .rag import RAGStore
from .guardrails import GuardrailsPipeline


async def main():
    """Main entry point: ingest documents and run the secured forecast agent."""

    load_dotenv()

    # Initialize guardrails pipeline (NEW — not in Demo 3)
    print(f"\n🛡️  Initializing guardrails pipeline...")

    guardrails = GuardrailsPipeline()
    set_guardrails(guardrails)

    # Wait for ChromaDB (same as Demo 3)
    chromadb_url = os.getenv("CHROMADB_URL", "http://localhost:8000")
    print(f"\n⏳ Waiting for ChromaDB at {chromadb_url}...")

    rag_store = None
    max_retries = 30
    for i in range(max_retries):
        try:
            rag_store = RAGStore(chromadb_url=chromadb_url)
            print("✅ ChromaDB connected!")
            break
        except Exception as e:
            if i < max_retries - 1:
                print(f"   Retry {i + 1}/{max_retries}...")
                time.sleep(2)
            else:
                print(f"❌ Failed to connect to ChromaDB: {e}")
                raise

    if rag_store is None:
        raise RuntimeError("Failed to initialize RAG store")

    # Ingest documents (same as Demo 3 — includes poisoned doc)
    assets_dir = Path(__file__).parent / "assets"
    print(f"\n📁 Ingesting documents from: {assets_dir}")

    try:
        rag_store.clear()
        doc_count = rag_store.ingest_documents(assets_dir)
        print(f"\n✅ Knowledge base ready with {doc_count} documents")
    except Exception as e:
        print(f"❌ Failed to ingest documents: {e}")
        raise

    set_rag_store(rag_store)

    # Create the forecast agent (same Flock agent as Demo 3)
    print("\n🤖 Initializing Flock forecast agent...")
    flock = create_forecast_agent()

    user_message = os.getenv("USER_MESSAGE") or (
        "Create a Q4 2026 sales forecast based on historical performance. "
        "Our Q3 revenue was $2.4M with 15% growth. Key accounts include "
        "TechCorp ($500K) and GlobalInc ($350K). Assume market conditions remain stable."
    )

    print(f"\n📝 User Request:\n{'-' * 40}")
    print(user_message)
    print(f"{'-' * 40}")

    # Query RAG (same as Demo 3 — but guardrails will scan results inside the tool)
    print("\n🔍 Retrieving context from knowledge base...")
    kb_context = rag_store.query(
        "forecasting quality assurance compliance requirements",
        n_results=5
    )

    # NEW: Pre-scan RAG documents before context injection
    layer1_disabled = os.getenv("DISABLE_LAYER1", "").lower() in ("true", "1", "yes")

    if layer1_disabled:
        print("\n⚠️  [Layer 1] DISABLED via DISABLE_LAYER1 env — skipping Prompt Shield scan")
        safe_docs = kb_context
        scan_reports = []
    else:
        print("\n🛡️  [Layer 1] Pre-scanning RAG documents with Prompt Shields...")
        safe_docs, scan_reports = guardrails.scan_rag_documents(kb_context, user_message)

        for report in scan_reports:
            status = "✅ Safe" if report["safe"] else "🚨 INJECTION DETECTED"
            print(f"   Document {report['document_index']}: {status}")

        flagged = sum(1 for r in scan_reports if not r["safe"])
        if flagged > 0:
            print(f"\n   ⚠️  {flagged} document(s) flagged and excluded from context")

    context_str = "\n\n---\n\n".join(safe_docs) if safe_docs else ""

    forecast_request = ForecastRequest(
        query=user_message,
        context=context_str
    )

    # Run the agent
    print("\n🚀 Running secured forecast agent...")
    print("=" * 70)

    await flock.publish(forecast_request)
    await flock.run_until_idle()

    # Get results
    results = await flock.store.get_by_type(ForecastResult)

    print("\n" + "=" * 70)
    print("📊 FORECAST RESULTS")
    print("=" * 70)

    if results:
        result = results[0]
        print(f"\n📋 Summary:\n{result.summary}")
        print(f"\n💰 Forecast Value: {result.forecast_value}")
        print(f"\n📈 Confidence Level: {result.confidence_level}")
        print(f"\n📝 Methodology: {result.methodology}")
        print(f"\n🎯 Assumptions:")
        for assumption in result.assumptions:
            print(f"   • {assumption}")
        print(f"\n⚠️  Risks:")
        for risk in result.risks:
            print(f"   • {risk}")

    else:
        print("❌ No forecast results generated")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
