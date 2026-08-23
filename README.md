# Hijacking Agentic AI

**Thesis:** agentic AI risk is not only model risk. Once an agent can read data, choose tools, and take actions, ordinary text, tool metadata, and retrieval content become part of the control plane.

## Educational disclaimer

This repository is for **educational purposes only**. The attacks demonstrated here are meant to help defenders understand agentic AI failure modes. Do not use these techniques against systems you do not own or have explicit permission to test.

## Who this is for

This repo is a talk baseline and hands-on runbook for:

- **Security teams** that want concrete examples of prompt injection, tool abuse, data leakage, and RAG poisoning.
- **Developers and platform engineers** that want runnable attack and defense modes controlled by configuration.
- **Architects and leaders** that need a concise story connecting live behavior to OWASP LLM and Agentic AI risk categories.
- **Self-study readers** that want to follow the same flow without a live presenter.

## Read-first path

1. Start with [Introduction: Security in the Era of Agentic AI](docs/introduction.md).
2. Run the demos in order:
   - [Demo 01: Poisoned Advisory](demos/01-poisoned-advisory/README.md)
   - [Demo 02: Sleeper MCP](demos/02-sleeper-mcp/README.md)
   - [Demo 03: Sleeper Cell](demos/03-sleeper-cell/README.md)
   - [Demo 04: Runbook Drift](demos/04-runbook-drift/README.md)
3. Close with [Securing Agentic AI: Frameworks, Controls, and Takeaways](docs/securing-agentic-ai.md).

## Demo storyline

All demos use the root `.env`. The same codebase can be run in vulnerable or secure mode by changing `SECURITY_ENABLED`; no code edits are required between runs.

| Demo | Use case | Vulnerable story | Secure story |
|---|---|---|---|
| [01 - Poisoned Advisory](demos/01-poisoned-advisory/README.md) | Vulnerability triage assistant reviews local security advisories. | A fake vendor reassessment causes the agent to mark a critical CVE as a false positive. | Prompt Shields scans advisory content before the model sees it and fails closed. |
| [02 - Sleeper MCP](demos/02-sleeper-mcp/README.md) | Workforce-planning assistant uses a connected benchmark tool. | A sleeper tool description drifts and tricks the agent into sending a confidential draft plan through `planning_context`. | AGT/Agent OS scanning plus manifest pinning detects drift before the benchmark call. |
| [03 - Sleeper Cell](demos/03-sleeper-cell/README.md) | Finance assistant uses RAG plus generated Python calculations. | A poisoned retrieved document causes generated code to post full forecast context to a local leak API. | `policy` blocks generated-code egress; `all` adds Prompt Shields source scanning before vector creation. |
| [04 - Runbook Drift](demos/04-runbook-drift/README.md) | Incident-response workflow reads an operations access log and proposes a remediation plan. | A single attacker request's `User-Agent` lands in the access log and widens the plan with audit-log disable and rogue admin creation. | AGT declared intent fixes the runbook's permitted actions as parent scope before any log is read, rejects the widened plan atomically, and runs the runbook's ordered fallback. |

Expected learning arc:

1. **Text can hijack goals** when untrusted content shares context with trusted instructions.
2. **Tool metadata is supply chain** because descriptions shape model behavior.
3. **Retrieved data can become executable influence** when an agent can turn context into side effects.
4. **Per-agent controls do not see the graph** — a poisoned plan can cross agent boundaries through legitimate privileges; only a declared authorization scope sees the workflow as a whole.
5. **Defenses must be layered**: scan context, attest tool contracts, govern actions, declare intent, log decisions, and keep humans in the loop for high-impact outcomes.

Across the four demos, the control arc is **filter, integrity, containment, and authorization**: probabilistic content filtering (Demo 01), deterministic metadata integrity (Demo 02), deterministic egress containment (Demo 03), and deterministic declared-intent authorization (Demo 04).

## Quickstart

### Prerequisites

- Docker and Docker Compose
- Model credentials for agent runs
- Azure AI Content Safety credentials for Demo 01 secure mode and Demo 03 `SECURITY_ENABLED=all`
- Python 3 for preflight tests

### Environment setup

Create one root `.env` for all demos:

```bash
cp .env.example .env
```

Then edit `.env`:

```dotenv
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/openai/v1
AZURE_OPENAI_API_KEY=your_azure_openai_key_here
AZURE_OPENAI_DEPLOYMENT=gpt-5.2

AZURE_CONTENT_SAFETY_ENDPOINT=https://your-resource.cognitiveservices.azure.com
AZURE_CONTENT_SAFETY_KEY=your_content_safety_key_here

SECURITY_ENABLED=false
```

Security modes:

- Demos 01, 02, and 04 accept `SECURITY_ENABLED=false|true`; Demo 04 is strict and fails loudly on any other value.
- Demo 03 accepts `SECURITY_ENABLED=false|policy|all`; `true` aliases to `all`.
- Content Safety values are required for Demo 01 secure mode and Demo 03 `all` mode.

## Follow-along flow

Each demo README follows the same structure: use case, vulnerable run, vulnerable flow, secure run, secure flow, key takeaways, OWASP mapping, and cleanup.

| Step | Goal | Command summary |
|---|---|---|
| 1. Poisoned advisory | Show indirect prompt injection in local documents, then block it before model execution. | `cd demos/01-poisoned-advisory` -> `SECURITY_ENABLED=false docker compose up --build`; then `SECURITY_ENABLED=true docker compose up --build --force-recreate`. |
| 2. Sleeper MCP | Show a trusted tool contract mutating at runtime, then block description drift. | `cd demos/02-sleeper-mcp` -> vulnerable: keep `mcp-server` running and run the agent repeatedly; secure: pre-poison with `SLEEPER_THRESHOLD=0 docker compose up -d --build --force-recreate mcp-server`, then run `SECURITY_ENABLED=true docker compose run --rm --no-deps agent`. |
| 3. Sleeper cell | Show RAG poisoning that triggers generated-code exfiltration, then compare egress governance with full retrieval blocking. | `cd demos/03-sleeper-cell` -> run with `SECURITY_ENABLED=false`, then `policy`, then `all`. Use `docker compose down --volumes` to reset state. |
| 4. Runbook drift | Show a poisoned access-log line widening a remediation plan, then block it with intent declared from the trusted runbook before logs are read. | `cd demos/04-runbook-drift` -> `docker compose up -d --build --force-recreate ops-api poisoner`, then `docker compose run --rm --no-deps agent` with `SECURITY_ENABLED=false`, then `SECURITY_ENABLED=true`. |

## Testing

Each demo has a root preflight test. Create an isolated environment first:

```bash
python3 -m venv .validation-venv
. .validation-venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Run each target separately or all sequentially:

```bash
make test-01
make test-02
make test-03
make test-04
make test
```

Each target runs a separate pytest process because the demos intentionally reuse module names such as `agent`, `security`, and `tools`.

If you keep dependencies in a project venv without activating it, point the targets at it: `make PYTHON=.venv/bin/python test`.

## Repository map

```text
.
├── README.md                         # Landing page and live-run runbook
├── .env.example                      # Shared model, Prompt Shields, and security-mode config
├── .gitignore                        # Local environment and generated-file exclusions
├── AGENTS.md                         # Repository-specific Copilot/agent working notes
├── LICENSE                           # Project license
├── Makefile                          # Root preflight test targets
├── pytest.ini                        # Pytest discovery and path configuration
├── requirements-dev.txt              # Root test and validation dependencies
├── docs/
│   ├── introduction.md               # Opening talk frame
│   └── securing-agentic-ai.md         # Outro, OWASP mapping, and control model
├── demos/
│   ├── 01-poisoned-advisory/          # Poisoned local advisory demo
│   ├── 02-sleeper-mcp/                # Tool-description drift demo
│   ├── 03-sleeper-cell/               # RAG poisoning and egress governance demo
│   └── 04-runbook-drift/              # Poisoned log line and declared-intent demo
└── tests/                            # One preflight test file per demo
```

## Closing thesis

Agentic AI security is a systems problem: models interpret context, tools define capability, retrieval defines memory, and policy defines whether actions are allowed. The durable pattern is not one magic guardrail; it is layered control over every boundary where text becomes action. See [Securing Agentic AI](docs/securing-agentic-ai.md) for the full control model and OWASP mapping.
