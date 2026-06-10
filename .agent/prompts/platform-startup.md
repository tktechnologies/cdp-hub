# Platform agent startup

**Humans:** use [new-chat.md](new-chat.md) (copy-paste block) at the start of every Cursor session.

**Agents:** follow the bootstrap below for monorepo-wide or n8n router work.

## Bootstrap

1. Read `AGENTS.md` and `docs/ARCHITECTURE.md`.
2. Read `docs/n8n/LIVE_WORKFLOWS.md` (IDs + **publish reality**) and `docs/architecture/DUAL_PIPELINE.md`.
3. Read `docs/architecture/AGENT_ARCHITECTURE.md`, `.agent/index.md`, `.agent/rules.md`.
4. Read `.agent/memory/implementation-state.md` — **current snapshot** at top; ignore superseded version UUIDs in changelog.
5. For Sheets/callback/reporting work, read `.agent/rules/google-sheets.md` and `.agent/knowledge/google-sheets-reporting.md`: `FOUND_PRICE` + `has_valid_price=true` is the only found-price success; row existence in `Detalhado` is not success; blocked/captcha/403 is `BLOCKED`, not `NOT_FOUND`.
   Detalhado seller metadata is `vendedor`, `uf`, `empresa`, `cnpj`; `estado` is input-alias only.
6. Use `docs/PLATFORM_OVERVIEW.md` only for API/Azure tables.
7. `git status --short` — never revert user changes.

## Classify the task

| Signal | Tier |
|--------|------|
| `n8n/src`, `.analisar`, platform workflow sync | Platform → `n8n-router-sync` skill |
| Playwright, scrape cache, Celery | Scraper → `scrapers/AGENTS.md` |
| API Diversos/StokAPI jobs, Redis Streams worker | StokAPI → `muvstok-api/AGENTS.md` |
| Only `cdp_scraper.json` flatten logic | Scraper service |
| Only `cdp_stokapi.json` | StokAPI service |

## n8n facts

- Dispatch: **only** `cdp_router` (ID in `docs/n8n/LIVE_WORKFLOWS.md` + `.agent/memory/implementation-state.md`)
- Webhooks: `scraper-result`, `muvstok-result` (stable)
- Sync: `make sync-n8n` — **never** without user approval
- DEV sync: `make n8n-dev-workflows` then `make sync-n8n-dev` with approval
- **Code-only** (`n8n/src/`): inject script + sync. **Graph/node changes**: MCP `update_workflow` `operations` + publish — sync alone may not update live graph ([LIVE_WORKFLOWS.md](../../docs/n8n/LIVE_WORKFLOWS.md))

## Agent docs

- Project-owned agent guidance lives in `.agent/` workspaces.
- Task-scoped rule summaries live in `.agent/rules/`.
- Cross-service ownership maps live in `.agent/knowledge/`.

## End of turn

- Update platform or service `implementation-state.md` if deployment facts changed
- State which tiers were touched and which quality gates were run
