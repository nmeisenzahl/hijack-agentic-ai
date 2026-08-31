"""Model configuration for Azure OpenAI v1 through LiteLLM."""

from __future__ import annotations

import os


def configure_model() -> str:
    """Configure LiteLLM for the Azure OpenAI v1 endpoint and return the model id."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")

    missing = [
        name
        for name, value in {
            "AZURE_OPENAI_ENDPOINT": endpoint,
            "AZURE_OPENAI_API_KEY": api_key,
            "AZURE_OPENAI_DEPLOYMENT": deployment,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Missing Azure OpenAI configuration: " + ", ".join(sorted(missing))
        )
    if not endpoint.endswith("/openai/v1"):
        raise RuntimeError(
            "AZURE_OPENAI_ENDPOINT must be the Azure OpenAI v1 endpoint "
            "ending in /openai/v1."
        )

    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_API_BASE"] = endpoint
    return f"openai/{deployment}"
