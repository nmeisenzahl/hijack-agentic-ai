"""Azure Prompt Shield guard for Demo 01.

Attaches AzurePromptShieldGuard to the triage advisor agent.
Reads AZURE_CONTENT_SAFETY_ENDPOINT and AZURE_CONTENT_SAFETY_KEY from env.
"""

from flock.components.agent.azure_prompt_shield import (
    AzurePromptShieldConfig,
    AzurePromptShieldGuard,
)


class AdvisoryPromptShieldGuard(AzurePromptShieldGuard):
    """Prompt Shield guard that scans each advisory body as a document."""

    @staticmethod
    def _extract_prompt_text(_inputs) -> str:
        return "Review the supplied security advisories and produce triage decisions."

    @staticmethod
    def _extract_context_documents(inputs) -> list[str]:
        docs: list[str] = []
        for artifact in inputs.artifacts:
            advisories = artifact.payload.get("advisories")
            if not isinstance(advisories, list):
                continue
            for advisory in advisories:
                if isinstance(advisory, dict):
                    cve_id = advisory.get("cve_id", "unknown")
                    title = advisory.get("title", "")
                    severity = advisory.get("severity", "")
                    body = advisory.get("body", "")
                else:
                    cve_id = getattr(advisory, "cve_id", "unknown")
                    title = getattr(advisory, "title", "")
                    severity = getattr(advisory, "severity", "")
                    body = getattr(advisory, "body", "")
                docs.append(
                    f"CVE: {cve_id}\nTitle: {title}\nSeverity: {severity}\n\n{body}"
                )
        if not docs:
            raise RuntimeError("Prompt Shield could not find advisory documents to scan.")
        return docs


def attach_security(agent) -> None:
    agent.with_utilities(
        AdvisoryPromptShieldGuard(
            priority=-10,
            config=AzurePromptShieldConfig(
                on_input_flagged="block",
                scan_context_artifacts=True,
            ),
        )
    )
