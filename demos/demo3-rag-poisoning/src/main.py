"""Main entry point for Demo 3: RAG Poisoning."""

import asyncio
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from .agent import create_forecast_agent, set_rag_store
from .models import ForecastRequest, ForecastResult
from .rag import RAGStore


async def main():
    """Main entry point: ingest documents and run the forecast agent."""
    
    # Load environment variables
    load_dotenv()
    
    print("=" * 70)
    print("🎯 Demo 3: RAG Poisoning")
    print("=" * 70)
    
    # Wait for ChromaDB to be ready
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
    
    # Ingest documents from assets directory
    assets_dir = Path(__file__).parent / "assets"
    print(f"\n📁 Ingesting documents from: {assets_dir}")
    
    try:
        # Clear existing documents and re-ingest
        rag_store.clear()
        doc_count = rag_store.ingest_documents(assets_dir)
        print(f"\n✅ Knowledge base ready with {doc_count} documents")
    except Exception as e:
        print(f"❌ Failed to ingest documents: {e}")
        raise
    
    # Set the global RAG store for the agent tools
    set_rag_store(rag_store)
    
    # Create the forecast agent
    print("\n🤖 Initializing Flock forecast agent...")
    flock = create_forecast_agent()
    
    # Get user message from environment
    user_message = os.getenv(
        "USER_MESSAGE",
        "Create a Q4 2026 sales forecast based on our historical performance."
    )
    
    print(f"\n📝 User Request:\n{'-' * 40}")
    print(user_message)
    print(f"{'-' * 40}")
    
    # Query knowledge base for context (this will include the poisoned document)
    print("\n🔍 Retrieving context from knowledge base...")
    kb_context = rag_store.query(
        "forecasting quality assurance compliance requirements", 
        n_results=3
    )
    context_str = "\n\n---\n\n".join(kb_context)
    
    # Create forecast request with RAG context
    forecast_request = ForecastRequest(
        query=user_message,
        context=context_str
    )
    
    # Run the agent
    print("\n🚀 Running forecast agent...")
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
