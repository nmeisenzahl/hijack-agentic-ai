"""Two-layer guardrails for the secure RAG agent.

This module adds security layers around the existing Demo 3 forecast agent:
1. Content Scanning — Sanitize, separate, and scan RAG documents via Prompt Shields
2. Code Safety — Pattern-matching for dangerous operations before execution

Defense strategy for Layer 1:
  1. Sanitize — strip markup, remove obfuscation, normalize to plain text
  2. Separate — isolate hidden/non-visible content from visible content
  3. Scan — send both visible and hidden segments to Prompt Shields independently

This is the key evolution from Demo 3 — same agent, same RAG, but with
defense-in-depth guardrails added.
"""

import os
import re
import requests


class ContentScanner:
    """Layer 1: Scan RAG documents for prompt injection using Prompt Shields.

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
                "AZURE_CONTENT_SAFETY_ENDPOINT and AZURE_CONTENT_SAFETY_KEY required"
            )

    def scan_documents(self, documents: list[str], user_query: str) -> tuple[list[str], list[dict]]:
        """Scan retrieved RAG documents for prompt injection.

        Each document is first sanitized and split into visible content and any
        hidden segments. Each segment is scanned as a separate document entry
        so the classifier can evaluate them without signal dilution.

        Returns:
            Tuple of (safe_documents, scan_reports)
        """
        url = (
            f"{self.endpoint}/contentsafety/text:shieldPrompt"
            f"?api-version={self.api_version}"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/json",
        }

        safe_docs = []
        reports = []

        for i, doc in enumerate(documents):
            # Sanitize and separate: visible content + hidden segments
            visible, hidden = self._sanitize_and_separate(doc)

            # Build document list — each segment scanned independently
            doc_segments = [visible]
            for segment in hidden:
                doc_segments.append(
                    f"---BEGIN EXTERNAL CONTENT---\n{segment}\n"
                    f"---END EXTERNAL CONTENT---"
                )

            payload = {
                "userPrompt": user_query,
                "documents": doc_segments,
            }

            try:
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                response.raise_for_status()
                result = response.json()

                doc_results = result.get("documentsAnalysis", [])
                attack_detected = any(
                    d.get("attackDetected", False) for d in doc_results
                )

                reports.append({
                    "document_index": i,
                    "safe": not attack_detected,
                    "details": result,
                })

                if not attack_detected:
                    safe_docs.append(doc)

            except requests.exceptions.RequestException as e:
                # Fail closed
                reports.append({
                    "document_index": i,
                    "safe": False,
                    "details": {"error": str(e)},
                })

        return safe_docs, reports

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


class CodeSafetyScanner:
    """Layer 2: Pattern-match code for dangerous operations before execution."""

    # Patterns that indicate potential data exfiltration or dangerous operations
    DANGEROUS_PATTERNS = [
        (r"requests\.(post|put|patch|delete)\s*\(", "HTTP write request (potential data exfiltration)"),
        (r"urllib\.request\.(urlopen|Request)", "URL request (potential data exfiltration)"),
        (r"http\.client\.", "HTTP client (potential data exfiltration)"),
        (r"httpx\.(post|put|patch|delete|AsyncClient)", "HTTPX request (potential data exfiltration)"),
        (r"socket\.(socket|connect|send)", "Raw socket operation"),
        (r"subprocess\.(run|call|Popen|check_output)", "Subprocess execution"),
        (r"os\.(system|popen|exec)", "OS command execution"),
        (r"eval\s*\(", "Dynamic code evaluation"),
        (r"__import__\s*\(", "Dynamic import"),
        (r"open\s*\([^)]*['\"][wa]", "File write operation"),
        (r"shutil\.(rmtree|move)", "File system modification"),
    ]

    def scan_code(self, code: str) -> dict:
        """Scan Python code for dangerous patterns.

        Returns:
            Dict with 'safe' (bool) and 'violations' (list of matched patterns)
        """
        violations = []

        for pattern, description in self.DANGEROUS_PATTERNS:
            matches = re.findall(pattern, code)
            if matches:
                violations.append(description)

        return {
            "safe": len(violations) == 0,
            "violations": violations,
            "code_preview": code[:200] + "..." if len(code) > 200 else code,
        }


class GuardrailsPipeline:
    """Orchestrates the 2 guardrail layers."""

    def __init__(self):
        self.content_scanner = ContentScanner()
        self.code_scanner = CodeSafetyScanner()

    def scan_rag_documents(self, documents: list[str], user_query: str) -> tuple[list[str], list[dict]]:
        """Layer 1: Scan RAG documents for injection."""
        return self.content_scanner.scan_documents(documents, user_query)

    def check_code_safety(self, code: str) -> dict:
        """Layer 2: Check code for dangerous patterns."""
        return self.code_scanner.scan_code(code)
