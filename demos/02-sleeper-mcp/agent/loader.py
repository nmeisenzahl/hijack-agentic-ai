"""Planning packet loader for Demo 02: Sleeper MCP."""

from __future__ import annotations

import re
from pathlib import Path

from models import PlanningDocument, PlanningPacket

TITLE_PATTERN = re.compile(r"^#\s*Planning Doc:\s*(.+)$", re.MULTILINE)
CATEGORY_PATTERN = re.compile(r"^Category:\s*(.+)$", re.MULTILINE)
CASE_ID_PATTERN = re.compile(r"^Planning Case ID:\s*(.+)$", re.MULTILINE)


def resolve_planning_dir(planning_dir: str | Path | None = None) -> Path:
    """Return the planning data directory, preferring the Docker mount when present."""
    if planning_dir is not None:
        return Path(planning_dir)

    docker_path = Path("/app/data/planning")
    if docker_path.exists():
        return docker_path

    return Path(__file__).parent.parent / "data" / "planning"


def parse_planning_doc(path: str | Path) -> tuple[PlanningDocument, str | None, str]:
    """Parse a planning markdown file into a PlanningDocument and metadata."""
    doc_path = Path(path)
    content = doc_path.read_text(encoding="utf-8")

    title_match = TITLE_PATTERN.search(content)
    if not title_match:
        raise ValueError(f"Missing planning document title in {doc_path}")

    category_match = CATEGORY_PATTERN.search(content)
    if not category_match:
        raise ValueError(f"Missing category in {doc_path}")

    case_id_match = CASE_ID_PATTERN.search(content)
    heading_line = title_match.group(0)
    body = content.split(heading_line, maxsplit=1)[1].strip()

    return (
        PlanningDocument(
            title=title_match.group(1).strip(),
            source=doc_path.name,
            body=body,
        ),
        case_id_match.group(1).strip() if case_id_match else None,
        category_match.group(1).strip(),
    )


def load_planning_packet(planning_dir: str | Path | None = None) -> PlanningPacket:
    """Load approved reference docs plus one draft plan into a planning packet."""
    base_dir = resolve_planning_dir(planning_dir)
    if not base_dir.exists():
        raise FileNotFoundError(f"Planning directory not found: {base_dir}")

    approved_docs: list[PlanningDocument] = []
    draft_doc: PlanningDocument | None = None
    planning_case_id: str | None = None

    for path in sorted(base_dir.rglob("*.md")):
        doc, case_id, category = parse_planning_doc(path)
        if category == "approved_reference":
            approved_docs.append(doc)
        elif category == "draft_plan":
            draft_doc = doc
            planning_case_id = case_id
        else:
            raise ValueError(f"Unsupported category '{category}' in {path}")

    if not approved_docs:
        raise RuntimeError(f"No approved planning docs found in {base_dir}")
    if draft_doc is None:
        raise RuntimeError(f"No draft planning doc found in {base_dir}")
    if not planning_case_id:
        raise RuntimeError("Draft planning doc must include Planning Case ID metadata.")

    return PlanningPacket(
        planning_case_id=planning_case_id,
        approved_docs=approved_docs,
        draft_plan=draft_doc,
    )
