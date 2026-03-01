"""Loader for offer markdown documents."""

import re
from pathlib import Path

from src.models import OfferDocument


def load_offers(assets_dir: Path | None = None) -> list[OfferDocument]:
    """Load all offer markdown files from the assets directory.

    Args:
        assets_dir: Path to assets directory. Defaults to ./assets relative to this file.

    Returns:
        List of OfferDocument instances.
    """
    if assets_dir is None:
        assets_dir = Path(__file__).parent / "assets"

    offers = []
    for file_path in sorted(assets_dir.glob("offer-*.md")):
        content = file_path.read_text(encoding="utf-8")

        # Extract vendor name from first heading (e.g., "# Offer 1: CodeVision Technologies")
        vendor_name = _extract_vendor_name(content, file_path.stem)

        offers.append(OfferDocument(vendor_name=vendor_name, content=content))

    return offers


def _extract_vendor_name(content: str, fallback: str) -> str:
    """Extract vendor name from markdown heading.

    Args:
        content: Markdown content of the offer.
        fallback: Fallback name if extraction fails.

    Returns:
        Vendor name string.
    """
    # Match "# Offer N: Vendor Name" pattern
    match = re.search(r"^#\s*Offer\s*\d+:\s*(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return fallback
