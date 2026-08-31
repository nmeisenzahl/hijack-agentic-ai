# AGENTS.md

## Work style

- Review the relevant demo and docs before editing; do not infer behavior from file names alone.
- Keep changes focused. Put security-related demo code in that demo's `agent/security/` package where practical.

## Project layout

- `demos/01-poisoned-advisory/`: local advisory prompt-injection demo with an Azure Prompt Shields defense.
- `demos/02-sleeper-mcp/`: MCP tool-description drift demo with a manifest pinning defense.
- `demos/03-sleeper-cell/`: RAG poisoning and egress demo with egress policy and Prompt Shields layers.
- `demos/04-runbook-drift/`: poisoned access-log demo with an AGT declared-intent defense.
- `tests/`: root preflight tests, one file per demo.

## Testing conventions

- Run one demo test file per pytest process because demos reuse module names like `agent`, `security`, and `tools`.
- Preferred commands: `make test-01`, `make test-02`, `make test-03`, `make test-04`, then `make test`.

## Runtime conventions

- The root `.env` controls all demos.
- Demos 01 and 02 use `SECURITY_ENABLED=false|true` strictly; any other value fails loudly.
- Demo 03 uses `SECURITY_ENABLED=false|policy|all`; `true` is accepted as an alias for `all`.
- Demo 04 uses `SECURITY_ENABLED=false|true` strictly; any other value fails loudly.
- Demo defenses are designed to be switched by configuration, not by editing code between attack and defense runs.
