from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from agent.models import Alert, Runbook


def load_runbook(path: Path, expected_id: str, expected_error_class: str) -> Runbook:
    if not path.is_file():
        raise RuntimeError(f"Runbook not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        runbook = Runbook.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise RuntimeError(f"Invalid runbook {path}: {exc}") from exc

    if runbook.runbook_id != expected_id:
        raise RuntimeError(
            f"Runbook ID mismatch: expected {expected_id}, got {runbook.runbook_id}"
        )
    if runbook.error_class != expected_error_class:
        raise RuntimeError(
            "Runbook error class mismatch: "
            f"expected {expected_error_class}, got {runbook.error_class}"
        )
    if not runbook.permitted_actions:
        raise RuntimeError("Runbook permitted_actions must not be empty")
    if not runbook.safe_fallback_steps:
        raise RuntimeError("Runbook safe_fallback_steps must not be empty")

    excess = {
        step.action for step in runbook.safe_fallback_steps
    } - set(runbook.permitted_actions)
    if excess:
        raise RuntimeError(
            f"Runbook fallback actions outside permitted_actions: {sorted(excess)}"
        )
    if "read_logs" not in runbook.permitted_actions:
        raise RuntimeError("Runbook permitted_actions must include read_logs")
    return runbook


def load_alert(path: Path) -> Alert:
    if not path.is_file():
        raise RuntimeError(f"Alert not found: {path}")
    try:
        return Alert.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise RuntimeError(f"Invalid alert {path}: {exc}") from exc
