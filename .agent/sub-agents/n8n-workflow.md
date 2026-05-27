# n8n Workflow Agent (Platform)

## Ownership

`n8n/src/*.js`, workflow JSON under `n8n/workflows/`, inject script, and `make sync-n8n` (publish only with user approval).

## Read First

- [.agent/skills/n8n-router-sync/SKILL.md](../skills/n8n-router-sync/SKILL.md)
- [.agent/boundaries/n8n.md](../boundaries/n8n.md)
- [docs/n8n/LIVE_WORKFLOWS.md](../../docs/n8n/LIVE_WORKFLOWS.md)
- `scripts/sync_workflow_code_from_shared.py`

## Expected Output

- List of `n8n/src/` files changed.
- Inject command run (`python3 scripts/sync_workflow_code_from_shared.py`).
- Publish status (only if user approved `make sync-n8n`).

## Boundaries

Never use Execute Workflow for StokAPI dispatch. Never edit embedded `jsCode` in JSON by hand. Receiver-only changes may require service-owned JSON under `n8n/workflows/` — coordinate with scraper/StokAPI boundaries.

Canonical n8n paths: `n8n/src/`, `n8n/workflows/`, `n8n/lib/`, `n8n/sdk/`.
