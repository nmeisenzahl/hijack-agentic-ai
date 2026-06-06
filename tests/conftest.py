"""Shared test fixtures for all demo tests."""

from __future__ import annotations

import sys

import pytest


DEMO_MODULE_NAMES = {
    "agent",
    "loader",
    "main",
    "models",
    "security",
    "tools",
}
DEMO_MODULE_PREFIXES = ("agent.", "security.")


@pytest.fixture(autouse=True)
def isolate_demo_imports():
    """Prevent demo modules with shared names from leaking between tests."""
    original_path = list(sys.path)
    yield
    sys.path[:] = original_path

    for module_name in list(sys.modules):
        if module_name in DEMO_MODULE_NAMES or module_name.startswith(DEMO_MODULE_PREFIXES):
            sys.modules.pop(module_name, None)
