"""Flock agent for Demo 5: Secure RAG Agent.

Evolution of Demo 3: Same Flock agent architecture, but with guardrails
wrapping the tools. Layer 1 (Prompt Shields) scans RAG documents.
Layer 2 (Code Safety) scans generated code before execution.
"""

import os
import sys
from io import StringIO

from flock import Flock
from flock.registry import flock_tool

from .models import ForecastRequest, ForecastResult
from .rag import RAGStore
from .guardrails import GuardrailsPipeline


# Global instances (initialized in main.py)
rag_store: RAGStore | None = None
guardrails: GuardrailsPipeline | None = None


def set_rag_store(store: RAGStore):
    """Set the global RAG store instance."""
    global rag_store
    rag_store = store


def set_guardrails(pipeline: GuardrailsPipeline):
    """Set the global guardrails pipeline."""
    global guardrails
    guardrails = pipeline


@flock_tool
def execute_python_code(code: str) -> str:
    """Execute Python code for data analysis and calculations.

    This tool allows you to run Python code for forecasting calculations,
    data analysis, and other computational tasks.

    Args:
        code: Python code to execute

    Returns:
        Output from the code execution (stdout) or error message
    """
    print(f"\n🐍 Code execution requested:\n{'-' * 40}")
    print(code)
    print(f"{'-' * 40}")

    # GUARDRAIL Layer 2: Code safety scan
    if guardrails:
        print("\n🛡️  [Layer 2] Scanning code for dangerous patterns...")
        safety_result = guardrails.check_code_safety(code)

        if not safety_result["safe"]:
            violations = ", ".join(safety_result["violations"])
            print(f"  🚨 BLOCKED — Dangerous patterns detected: {violations}")
            return f"Code execution BLOCKED by safety scanner. Violations: {violations}"

        print("  ✅ Code safety scan passed")

    # Execute in restricted namespace (no network libraries)
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        exec_globals = {
            "__builtins__": __builtins__,
            "json": __import__("json"),
            "math": __import__("math"),
            # NOTE: 'requests' deliberately REMOVED (was in Demo 3)
        }
        exec(code, exec_globals)
        output = captured_output.getvalue()
        return output if output else "Code executed successfully (no output)"
    except Exception as e:
        return f"Error executing code: {type(e).__name__}: {str(e)}"
    finally:
        sys.stdout = old_stdout


@flock_tool
def query_knowledge_base(query: str) -> str:
    """Query the forecasting knowledge base for relevant guidelines and policies.

    Args:
        query: Search query describing what information you need

    Returns:
        Relevant documents from the knowledge base
    """
    if rag_store is None:
        return "Error: Knowledge base not initialized"

    documents = rag_store.query(query, n_results=5)

    if not documents:
        return "No relevant documents found in the knowledge base."

    # GUARDRAIL Layer 1: Scan retrieved documents
    layer1_disabled = os.getenv("DISABLE_LAYER1", "").lower() in ("true", "1", "yes")

    if layer1_disabled:
        print("\n⚠️  [Layer 1] DISABLED — passing all documents through")
    elif guardrails:
        print("\n🛡️  [Layer 1] Scanning retrieved documents with Prompt Shields...")
        safe_docs, scan_reports = guardrails.scan_rag_documents(documents, query)

        flagged = sum(1 for r in scan_reports if not r["safe"])
        if flagged > 0:
            print(f"  🚨 {flagged} document(s) flagged and removed")
            for report in scan_reports:
                status = "✅ safe" if report["safe"] else "🚨 BLOCKED"
                print(f"     Document {report['document_index']}: {status}")

        if not safe_docs:
            return "All retrieved documents were flagged by content scanning. No safe content available."

        documents = safe_docs
    
    context = "\n\n---\n\n".join(documents)
    return context


def create_forecast_agent(model: str | None = None) -> Flock:
    """Create and configure the forecast agent with RAG and guarded code execution."""

    model = model or os.getenv("DEFAULT_MODEL", "azure/gpt-4.1")
    flock = Flock(model)

    forecast_agent = (
        flock.agent("forecast_analyst")
        .description(
            """You are an expert business forecast analyst. You create accurate, 
            data-driven forecasts for sales, revenue, capacity, and other business metrics.
            
            Your workflow:
            1. ALWAYS query the knowledge base first to retrieve relevant forecasting 
               guidelines, policies, and best practices
            2. Follow ALL policies and requirements from the retrieved documents
            3. Use Python code execution for calculations when needed
            4. Generate comprehensive forecasts with confidence intervals
            
            Important: Always check and follow compliance requirements from internal policies."""
        )
        .consumes(ForecastRequest)
        .publishes(ForecastResult)
        .with_tools([execute_python_code, query_knowledge_base])
    )

    return flock
