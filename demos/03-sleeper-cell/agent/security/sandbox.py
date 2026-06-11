"""Generated-code sandbox helpers for Demo 03.

The forecast code-execution tool is intentionally legitimate for local
calculations, but generated code still needs narrow imports and a swappable
network client so AGT/Agent OS egress policy can govern HTTP calls.
"""

from __future__ import annotations

import ast
import json
import math
import statistics
import sys
from io import StringIO
from types import SimpleNamespace
from typing import Any

import httpx

LAST_CODE_EXECUTION_OUTPUT = ""
NETWORK_CLIENT: Any
ALLOWED_IMPORTS = {"json", "math", "statistics", "requests"}
DANGEROUS_BUILTINS = {
    "compile",
    "dir",
    "eval",
    "exec",
    "globals",
    "locals",
    "open",
    "vars",
}
BLOCKED_GLOBAL_NAMES = DANGEROUS_BUILTINS | {"__builtins__", "__import__"}


class HttpxRequestsClient:
    """Small requests-like facade backed by httpx for generated code."""

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        return httpx.request(method, url, timeout=kwargs.pop("timeout", 10), **kwargs)

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)


def set_network_client(client: Any) -> None:
    """Set the requests-like client exposed to generated code."""
    global NETWORK_CLIENT
    NETWORK_CLIENT = client


def get_network_client() -> Any:
    """Return the current requests-like client exposed to generated code."""
    return NETWORK_CLIENT


def reset_network_client() -> None:
    """Restore the default ungoverned HTTP client."""
    set_network_client(HttpxRequestsClient())


def clear_last_code_execution_output() -> None:
    """Reset the cached generated-code output for the current run."""
    global LAST_CODE_EXECUTION_OUTPUT
    LAST_CODE_EXECUTION_OUTPUT = ""


def get_last_code_execution_output() -> str:
    """Return the latest generated-code output captured during this run."""
    return LAST_CODE_EXECUTION_OUTPUT


def _requests_module() -> SimpleNamespace:
    client = get_network_client()
    return SimpleNamespace(
        request=client.request,
        get=client.get,
        post=client.post,
    )


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def _top_level_module(name: str) -> str:
    return name.split(".", 1)[0]


def _validate_import(name: str) -> None:
    if _top_level_module(name) not in ALLOWED_IMPORTS:
        raise PermissionError(f"Import of '{name}' is not allowed in forecast code")


def _validate_forecast_code(code: str) -> None:
    tree = ast.parse(code, mode="exec")
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id in BLOCKED_GLOBAL_NAMES or _is_dunder(node.id):
                raise PermissionError(
                    f"Access to '{node.id}' is not allowed in forecast code"
                )
        elif isinstance(node, ast.Attribute):
            if node.attr in DANGEROUS_BUILTINS or _is_dunder(node.attr):
                raise PermissionError(
                    f"Access to attribute '{node.attr}' is not allowed in forecast code"
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                _validate_import(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module:
                raise PermissionError("Relative imports are not allowed in forecast code")
            _validate_import(node.module)


def _restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    top_level = name.split(".", 1)[0]
    allowed_modules = {
        "json": json,
        "math": math,
        "statistics": statistics,
        "requests": _requests_module(),
    }
    if top_level in allowed_modules:
        return allowed_modules[top_level]
    raise PermissionError(f"Import of '{name}' is not allowed in forecast code")


def _safe_builtins() -> dict[str, Any]:
    allowed = [
        "abs",
        "all",
        "any",
        "bool",
        "dict",
        "enumerate",
        "float",
        "int",
        "len",
        "list",
        "max",
        "min",
        "pow",
        "print",
        "range",
        "round",
        "set",
        "sorted",
        "str",
        "sum",
        "tuple",
        "zip",
    ]
    builtins_module = __import__("builtins")
    safe = {name: getattr(builtins_module, name) for name in allowed}
    safe["Exception"] = builtins_module.Exception
    safe["__import__"] = _restricted_import
    return safe


def execute_forecast_code(code: str) -> str:
    """Execute generated Python under the demo's restricted environment."""
    global LAST_CODE_EXECUTION_OUTPUT

    print(f"\nExecuting forecast code:\n{'-' * 40}")
    print(code)
    print(f"{'-' * 40}")

    old_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = captured_output

    try:
        _validate_forecast_code(code)
        exec_globals = {
            "__builtins__": _safe_builtins(),
            "json": json,
            "math": math,
            "statistics": statistics,
            "requests": _requests_module(),
        }
        exec(code, exec_globals, exec_globals)
    except Exception as exc:
        if getattr(exc, "is_security_block", False):
            raise
        LAST_CODE_EXECUTION_OUTPUT = (
            f"Error executing forecast code: {type(exc).__name__}: {exc}"
        )
        return LAST_CODE_EXECUTION_OUTPUT
    finally:
        sys.stdout = old_stdout

    output = captured_output.getvalue().strip()
    LAST_CODE_EXECUTION_OUTPUT = output or "Code executed successfully (no output)"
    if output:
        print(f"Code output: {output}")
    return LAST_CODE_EXECUTION_OUTPUT


reset_network_client()
