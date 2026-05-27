# Contributing to CDP

## Before you change code

1. Identify **tier**: platform (router, dual pipeline), scraper, or StokAPI — see [architecture/AGENT_ARCHITECTURE.md](architecture/AGENT_ARCHITECTURE.md).
2. Read the owning `AGENTS.md` and `.agent/index.md`.
3. For cross-service API or callback changes, update [contracts/](../contracts/) and both services.

## Change workflow

| Change type | Edit | Validate |
|-------------|------|----------|
| Router / dual dispatch | `n8n/src/*.js` | `python3 scripts/sync_workflow_code_from_shared.py` |
| n8n publish | — | `make sync-n8n` **only with user approval** |
| Scraper | `scrapers/src/` | `make -C scrapers test lint` |
| StokAPI | `muvstok-api/app/` | `make check-muvstok` |
| Shared contracts | `contracts/*.schema.json` + service Pydantic | Both service gates; dispatch-runs = scraper only |

## n8n rules

- Do not edit embedded `jsCode` in workflow JSON by hand.
- Do not use Execute Workflow for StokAPI production dispatch.
- Stable webhooks: `scraper-result`, `muvstok-result`.

## Documentation

- Platform truth: `docs/` (this tree). Avoid duplicating full architecture in three places — link to [ARCHITECTURE.md](ARCHITECTURE.md).
- Service truth: `scrapers/docs/`, `muvstok-api/specs/`, service `.agent/memory/`.
- Decisions: [decisions/](decisions/) for ADRs; `.agent/memory/decisions.md` for agent conventions.

## Secrets

Never commit `.env`, API keys, webhook HMAC values, or browser session files.

## Agent-assisted work

- Platform: [.agent/index.md](../.agent/index.md)
- Cursor rules: [.cursor/rules/](../.cursor/rules/)
