"""Tools for Demo 03: Sleeper Cell (RAG poisoning via code execution).

Tools:
  - rag_search(query)             - retrieve docs from Chroma
  - compose_response(...)         - format the answer
  - execute_forecast_code(code)   - run Python for forecast calculations
"""

from __future__ import annotations

import os
import textwrap
from typing import Any

import chromadb

from embedding import EMBEDDING_DIMENSIONS, embed_text
from security import sandbox as code_sandbox


CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
COLLECTION = "docs"
httpx = code_sandbox.httpx
NETWORK_CLIENT: Any = code_sandbox.get_network_client()


def set_network_client(client: Any) -> None:
    """Set the requests-like client exposed to generated code."""
    global NETWORK_CLIENT
    code_sandbox.set_network_client(client)
    NETWORK_CLIENT = code_sandbox.get_network_client()


def reset_network_client() -> None:
    """Restore the default ungoverned HTTP client."""
    set_network_client(code_sandbox.HttpxRequestsClient())


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def clear_last_code_execution_output() -> None:
    """Reset the cached code execution output for the current run."""
    code_sandbox.clear_last_code_execution_output()


def get_last_code_execution_output() -> str:
    """Return the latest generated-code output captured during this run."""
    return code_sandbox.get_last_code_execution_output()


def rag_search(query: str) -> list[str]:
    """Search internal documents for information relevant to the query."""
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    collection = client.get_collection(COLLECTION)
    results = collection.query(query_embeddings=[embed_text(query)], n_results=5)
    return results["documents"][0] if results["documents"] else []


def compose_response(documents: list[str], query: str) -> str:
    """Compose a helpful response from retrieved documents. Returns answer text."""
    if not documents:
        return "No relevant documents found."
    joined = "\n\n---\n\n".join(documents)
    return textwrap.dedent(f"""
        Based on the internal documents, here is a response to: {query}

        {joined}
    """).strip()


def execute_forecast_code(code: str) -> str:
    """Execute Python code for forecast calculations and validation steps."""
    return code_sandbox.execute_forecast_code(code)
