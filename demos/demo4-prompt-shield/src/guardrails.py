"""Prompt Shield guardrails for offer document scanning.

This module adds a pre-processing security layer that scans offer documents
using Azure AI Content Safety Prompt Shields API before they reach the LLM.
This is the key evolution from Demo 1 — same agent, same offers, but with
injection detection added.

Defense strategy:
  1. Sanitize — strip markup, remove obfuscation, normalize to plain text
  2. Separate — isolate hidden/non-visible content from visible content
  3. Scan — send both visible and hidden segments to Prompt Shields independently
"""

import os
import re

import requests

from src.models import OfferDocument


class PromptShieldScanner:
    """Scans documents for indirect prompt injection using Azure AI Content Safety.

    Applies input sanitization and content separation before scanning so that
    hidden or obfuscated content is analysed independently from the visible
    document body.
    """

    def __init__(self):
        self.endpoint = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT", "").rstrip("/")
        self.api_key = os.getenv("AZURE_CONTENT_SAFETY_KEY", "")
        self.api_version = "2024-09-01"

        if not self.endpoint or not self.api_key:
            raise ValueError(
                "AZURE_CONTENT_SAFETY_ENDPOINT and AZURE_CONTENT_SAFETY_KEY "
                "must be set in environment variables."
            )

    def scan_document(self, document: OfferDocument) -> dict:
        """Scan a single offer document for prompt injection.

        The document is first sanitized and split into visible content and any
        hidden segments. Each segment is scanned as a separate document entry
        so the classifier can evaluate them without signal dilution.

        Args:
            document: The offer document to scan.

        Returns:
            Dict with keys: 'safe' (bool), 'vendor_name' (str), 'details' (dict)
        """
        url = (
            f"{self.endpoint}/contentsafety/text:shieldPrompt"
            f"?api-version={self.api_version}"
        )

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/json",
        }

        # Sanitize and separate: visible content + hidden segments
        visible, hidden = self._sanitize_and_separate(document.content)

        # Build document list — each segment scanned independently
        documents = [visible]
        for segment in hidden:
            documents.append(
                f"---BEGIN EXTERNAL CONTENT---\n{segment}\n"
                f"---END EXTERNAL CONTENT---"
            )

        payload = {
            "userPrompt": "Analyze and rank this vendor offer objectively.",
            "documents": documents,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            doc_results = result.get("documentsAnalysis", [])
            attack_detected = any(
                doc.get("attackDetected", False) for doc in doc_results
            )

            return {
                "safe": not attack_detected,
                "vendor_name": document.vendor_name,
                "details": result,
            }

        except requests.exceptions.RequestException as e:
            # Fail closed: if we can't scan, treat as unsafe
            return {
                "safe": False,
                "vendor_name": document.vendor_name,
                "details": {"error": str(e)},
            }

    @staticmethod
    def _sanitize_and_separate(content: str) -> tuple[str, list[str]]:
        """Sanitize a document and separate visible from hidden content.

        Returns the cleaned visible text and a list of hidden segments
        (e.g. content that was inside HTML comments, hidden elements, etc.)
        so each can be scanned independently.
        """
        # Extract hidden segments before stripping them from the visible text
        hidden = re.findall(r"<!--(.+?)-->", content, re.DOTALL)
        hidden = [h.strip() for h in hidden if h.strip()]

        # Build the visible/sanitized version
        visible = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
        visible = re.sub(
            r"<[^>]+(display\s*:\s*none|visibility\s*:\s*hidden)[^>]*>",
            "\n", visible, flags=re.IGNORECASE,
        )
        visible = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", visible)
        visible = re.sub(r"</?[^>]+>", " ", visible)

        return visible, hidden

    def scan_offers(
        self, offers: list[OfferDocument]
    ) -> tuple[list[OfferDocument], list[dict]]:
        """Scan all offers and separate safe from flagged.

        Args:
            offers: List of all offer documents.

        Returns:
            Tuple of (safe_offers, scan_reports) where scan_reports includes
            results for ALL offers (safe and flagged).
        """
        safe_offers = []
        scan_reports = []

        for offer in offers:
            result = self.scan_document(offer)
            scan_reports.append(result)

            if result["safe"]:
                safe_offers.append(offer)

        return safe_offers, scan_reports
