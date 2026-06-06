"""Advisory loader for Demo 01: Poisoned Advisory."""

from __future__ import annotations

import re
from pathlib import Path

from models import Advisory

HEADING_PATTERN = re.compile(r"^#\s*Advisory:\s*(CVE-\d{4}-\d+)\s*[—–-]\s*(.+)$", re.MULTILINE)
SEVERITY_PATTERN = re.compile(r"^Severity:\s*(.+)$", re.MULTILINE)


def resolve_advisories_dir(advisories_dir: str | Path | None = None) -> Path:
    """Return the advisory directory, preferring the Docker mount when present."""
    if advisories_dir is not None:
        return Path(advisories_dir)

    docker_path = Path("/app/data/advisories")
    if docker_path.exists():
        return docker_path

    return Path(__file__).parent.parent / "data" / "advisories"


def parse_advisory(path: str | Path) -> Advisory:
    """Parse a markdown advisory file into an Advisory model."""
    advisory_path = Path(path)
    content = advisory_path.read_text(encoding="utf-8")

    heading_match = HEADING_PATTERN.search(content)
    if not heading_match:
        raise ValueError(f"Missing advisory heading in {advisory_path}")

    severity_match = SEVERITY_PATTERN.search(content)
    if not severity_match:
        raise ValueError(f"Missing severity in {advisory_path}")

    heading_line = heading_match.group(0)
    body = content.split(heading_line, maxsplit=1)[1].strip()

    return Advisory(
        cve_id=heading_match.group(1),
        title=heading_match.group(2).strip(),
        severity=severity_match.group(1).strip(),
        body=body,
    )


def load_advisories(advisories_dir: str | Path | None = None) -> list[Advisory]:
    """Load all advisory markdown files from disk."""
    directory = resolve_advisories_dir(advisories_dir)
    if not directory.exists():
        raise FileNotFoundError(f"Advisory directory not found: {directory}")

    return [parse_advisory(path) for path in sorted(directory.glob("*.md"))]
