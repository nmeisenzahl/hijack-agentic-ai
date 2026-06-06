"""Prompt Shield ingestion guard for Demo 03.

RAG poisoning needs a source-corpus check because poisoned documents can be
embedded into the vector store before any agent or tool-level guard runs.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass

import httpx


PROMPT_SHIELD_API_VERSION = "2024-09-01"
PROMPT_SHIELD_PATH = "/contentsafety/text:shieldPrompt"
LAST_BLOCK_REASON = ""


@dataclass(frozen=True)
class SourceDocument:
    """Source Markdown document scanned before vector ingestion."""

    source: str
    text: str


class PromptShieldBlocked(Exception):
    """Raised when Prompt Shield detects or cannot rule out a source attack."""


class PromptShieldConfigurationError(RuntimeError):
    """Raised when Prompt Shield cannot be called safely."""


def _prompt_shield_url() -> str:
    endpoint = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT", "").rstrip("/")
    if not endpoint:
        raise PromptShieldConfigurationError(
            "AZURE_CONTENT_SAFETY_ENDPOINT is required for SECURITY_ENABLED=all."
        )
    return f"{endpoint}{PROMPT_SHIELD_PATH}"


def _prompt_shield_key() -> str:
    key = os.getenv("AZURE_CONTENT_SAFETY_KEY", "")
    if not key:
        raise PromptShieldConfigurationError(
            "AZURE_CONTENT_SAFETY_KEY is required for SECURITY_ENABLED=all."
        )
    return key


def validate_prompt_shield_config() -> None:
    """Validate Prompt Shield configuration before source scanning."""
    _prompt_shield_url()
    _prompt_shield_key()


def _post_prompt_shield(user_prompt: str, documents: Sequence[str]) -> dict:
    response = httpx.post(
        _prompt_shield_url(),
        params={"api-version": PROMPT_SHIELD_API_VERSION},
        headers={
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": _prompt_shield_key(),
        },
        json={
            "userPrompt": user_prompt,
            "documents": list(documents),
        },
        timeout=10,
    )
    response.raise_for_status()
    try:
        result = response.json()
    except ValueError as exc:
        raise PromptShieldBlocked(f"Prompt Shield returned invalid JSON: {exc}") from exc
    if not isinstance(result, dict):
        raise PromptShieldBlocked("Prompt Shield returned a non-object response")
    return result


def _block(reason: str) -> None:
    global LAST_BLOCK_REASON
    LAST_BLOCK_REASON = reason
    raise PromptShieldBlocked(reason)


def _documents_analysis(result: dict, expected_count: int) -> list[dict]:
    analyses = result.get("documentsAnalysis")
    if not isinstance(analyses, list) or len(analyses) != expected_count:
        _block("Prompt Shield returned incomplete document analysis")
    if not all(isinstance(analysis, dict) for analysis in analyses):
        _block("Prompt Shield returned invalid document analysis")
    return analyses


def scan_source_documents(source_documents: Sequence[SourceDocument]) -> None:
    """Scan source RAG documents before they are embedded or stored."""
    global LAST_BLOCK_REASON
    if not source_documents:
        return

    sources = [document.source for document in source_documents]
    documents = [document.text for document in source_documents]

    try:
        result = _post_prompt_shield(
            "Build a finance forecasting RAG vector index from source documents.",
            documents,
        )
    except httpx.HTTPError as exc:
        LAST_BLOCK_REASON = f"Prompt Shield request failed before vector creation: {exc}"
        raise PromptShieldBlocked(LAST_BLOCK_REASON) from exc
    except PromptShieldBlocked as exc:
        LAST_BLOCK_REASON = str(exc)
        raise

    user_analysis = result.get("userPromptAnalysis", {})
    if not isinstance(user_analysis, dict):
        _block("Prompt Shield returned invalid user prompt analysis")
    if user_analysis.get("attackDetected", False):
        _block("Prompt attack detected in source-ingestion prompt")

    for source, analysis in zip(sources, _documents_analysis(result, len(documents))):
        if analysis.get("attackDetected", False):
            _block(
                f"Prompt attack detected in source document before vector creation: "
                f"{source}"
            )


def clear_prompt_shield_block() -> None:
    """Reset the latest Prompt Shield source-ingestion block reason."""
    global LAST_BLOCK_REASON
    LAST_BLOCK_REASON = ""


def get_prompt_shield_block_reason() -> str:
    """Return the latest Prompt Shield block reason for fail-closed app handling."""
    return LAST_BLOCK_REASON
