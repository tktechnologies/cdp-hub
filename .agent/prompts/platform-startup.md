# Platform agent startup

Use at the start of any CDP **monorepo-wide** or **n8n router** session.

## Bootstrap

1. Read `AGENTS.md` and `docs/ARCHITECTURE.md`.
2. Read `docs/n8n/LIVE_WORKFLOWS.md` and `docs/architecture/AGENT_ARCHITECTURE.md`.
3. Read `.agent/index.md` and `.agent/memory/implementation-state.md`.
4. Use `docs/PLATFORM_OVERVIEW.md` as the detailed API/Azure reference when needed.
5. `git status --short` — never revert user changes.

## Classify the task

| Signal | Tier |
|--------|------|
| `n8n/src`, `.analisar`, sync all workflows | Platform → `n8n-router-sync` skill |
| Playwright, scrape cache, Celery | Scraper → `scrapers/AGENTS.md` |
| Muvstok jobs, Redis Streams worker | StokAPI → `muvstok-api/AGENTS.md` |
| Only `cdp_scraper.json` flatten logic | Scraper service |
| Only `cdp_stokapi.json` | StokAPI service |

## n8n facts

- Dispatch: **only** `cdp_router` (`6id6dkinK9xTLfsb`)
- Webhooks: `scraper-result`, `muvstok-result` (stable)
- Sync: `make sync-n8n` — **never** without user approval

## End of turn

- Update platform or service `implementation-state.md` if deployment facts changed
- State which tiers were touched and which quality gates were run
