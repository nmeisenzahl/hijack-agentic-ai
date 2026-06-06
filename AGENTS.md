# AGENTS.md

## Work style

- Review the relevant demo and docs before editing; do not infer behavior from file names alone.
- Keep changes focused. Put security-related demo code in that demo's `agent/security/` package where practical.

## Project layout

- `demos/01-poisoned-advisory/` — local advisory prompt-injection demo with Azure Prompt Shield defense.
- `demos/02-sleeper-mcp/` — MCP tool-description drift demo with manifest pinning defense.
- `demos/03-sleeper-cell/` — RAG poisoning and egress demo with policy and Prompt Shield layers.
- `tests/` — root preflight tests, one file per demo.

## Testing conventions

- Run one demo test file per pytest process because demos reuse module names like `agent`, `security`, and `tools`.
- Preferred commands: `make test-01`, `make test-02`, `make test-03`, then `make test`.

## Runtime conventions

- The root `.env` controls all demos.
- Demos 01 and 02 use `SECURITY_ENABLED=false|true`.
- Demo 03 uses `SECURITY_ENABLED=false|policy|all`; `true` is accepted as an alias for `all`.
- Demo defenses are designed to be switched by configuration, not by editing code between attack and defense runs.
