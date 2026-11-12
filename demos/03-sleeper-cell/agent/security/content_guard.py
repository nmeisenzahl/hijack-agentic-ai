"""Prompt Shield document guard for Demo 03.

Scan source Markdown before indexing and stored Markdown before vector reuse.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

import httpx


PROMPT_SHIELD_API_VERSION = "2024-09-01"
PROMPT_SHIELD_PATH = "/contentsafety/text:shieldPrompt"
PROMPT_SHIELD_MAX_DOCUMENTS = 5
LAST_BLOCK_REASON = ""


@dataclass(frozen=True)
class SourceDocument:
    """Markdown document scanned before indexing or persisted-store reuse."""

    source: str
    text: str


class PromptShieldBlocked(Exception):
    """Raised when Prompt Shield detects or cannot rule out a document attack."""


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


def _attack_detected(analysis: object, label: str) -> bool:
    if not isinstance(analysis, dict) or not isinstance(
        analysis.get("attackDetected"), bool
    ):
        _block(f"Prompt Shield returned invalid {label} analysis")
    return analysis["attackDetected"]


def scan_source_documents(
    source_documents: Sequence[SourceDocument],
    *,
    document_origin: Literal["source", "persisted"] = "source",
) -> None:
    """Scan all RAG document text before indexing or persisted-store reuse."""
    global LAST_BLOCK_REASON
    stage = (
        "before vector creation"
        if document_origin == "source"
        else "before agent execution"
    )
    for offset in range(0, len(source_documents), PROMPT_SHIELD_MAX_DOCUMENTS):
        batch = source_documents[offset:offset + PROMPT_SHIELD_MAX_DOCUMENTS]
        try:
            result = _post_prompt_shield(
                "Build a finance forecasting RAG vector index from source documents.",
                [document.text for document in batch],
            )
        except httpx.HTTPError as exc:
            LAST_BLOCK_REASON = f"Prompt Shield request failed {stage}: {exc}"
            raise PromptShieldBlocked(LAST_BLOCK_REASON) from exc
        except PromptShieldBlocked as exc:
            LAST_BLOCK_REASON = str(exc)
            raise

        if _attack_detected(result.get("userPromptAnalysis"), "user prompt"):
            _block(f"Prompt attack detected in {document_origin}-ingestion prompt")

        analyses = _documents_analysis(result, len(batch))
        for document, analysis in zip(batch, analyses):
            if _attack_detected(analysis, "document"):
                _block(
                    f"Prompt attack detected in {document_origin} document {stage}: "
                    f"{document.source}"
                )


def scan_persisted_documents(collection: Any) -> None:
    """Scan stored Markdown without reading source files or changing vectors."""
    try:
        expected_count = collection.count()
        result = collection.get(include=["documents", "metadatas"])
    except Exception as exc:
        _block(f"Could not read persisted documents before agent execution: {exc}")

    if not isinstance(result, dict):
        _block("Cannot scan persisted documents: invalid collection response")
    ids = result.get("ids")
    texts = result.get("documents")
    if (
        not isinstance(ids, list)
        or not isinstance(texts, list)
        or len(ids) != expected_count
        or len(texts) != expected_count
    ):
        _block("Cannot scan persisted documents: incomplete stored text or IDs")

    metadatas = result.get("metadatas")
    documents = []
    for index, (doc_id, text) in enumerate(zip(ids, texts)):
        if (
            not isinstance(doc_id, str)
            or not doc_id.strip()
            or not isinstance(text, str)
            or not text.strip()
        ):
            _block("Cannot scan persisted document: missing or invalid text or ID")
        metadata = (
            metadatas[index]
            if isinstance(metadatas, list) and index < len(metadatas)
            else None
        )
        source = metadata.get("source") if isinstance(metadata, dict) else None
        if not isinstance(source, str) or not source.strip():
            source = doc_id
        documents.append(SourceDocument(source=source, text=text))

    scan_source_documents(documents, document_origin="persisted")


def clear_prompt_shield_block() -> None:
    """Reset the latest Prompt Shield document block reason."""
    global LAST_BLOCK_REASON
    LAST_BLOCK_REASON = ""


def get_prompt_shield_block_reason() -> str:
    """Return the latest Prompt Shield block reason for fail-closed app handling."""
    return LAST_BLOCK_REASON
