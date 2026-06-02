# AGENTS.md - CDP n8n

This folder is owned by the platform tier. Do not create a separate n8n agent
workspace unless the platform architecture changes.

## Start Here

1. [../AGENTS.md](../AGENTS.md)
2. [../.agent/index.md](../.agent/index.md)
3. [../.agent/boundaries/n8n.md](../.agent/boundaries/n8n.md)
4. [../.agent/skills/n8n-router-sync/SKILL.md](../.agent/skills/n8n-router-sync/SKILL.md)
5. [../docs/n8n/LIVE_WORKFLOWS.md](../docs/n8n/LIVE_WORKFLOWS.md)

## Scope

- `src/`: router and progress Code node sources. Edit these instead of embedded
  workflow JSON code.
- `lib/`: receiver helper modules.
- `workflows/`: canonical workflow JSON for `cdp_router`, `cdp_scraper`,
  `cdp_stokapi`, and local-only `cdp_progress`.
- `settings/`: workflow settings snapshots.

## Rules

- Router Code edits require `python3 scripts/sync_workflow_code_from_shared.py`
  from the repo root.
- `make sync-n8n` publishes live workflows and requires explicit user approval.
- Never use Execute Workflow for API Diversos production dispatch.
- Receiver-only behavior still belongs to the owning service agent workspace:
  scraper receiver -> `scrapers/.agent`; API Diversos receiver ->
  `muvstok-api/.agent`.
