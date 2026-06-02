# CDP Service Catalog

Root `.agent` owns the cross-service map. Service `.agent` workspaces own deep
implementation guidance.

## Services

| Service | Path | Agent entry | Owns | Gates |
|---------|------|-------------|------|-------|
| n8n platform | `n8n/` | [n8n/AGENTS.md](../../n8n/AGENTS.md) -> [.agent/boundaries/n8n.md](../boundaries/n8n.md) | `cdp_router`, shared router Code, workflow sync/publish | `python3 scripts/sync_workflow_code_from_shared.py`; `make sync-n8n` only with approval |
| Scraper | `scrapers/` | [scrapers/AGENTS.md](../../scrapers/AGENTS.md) -> [scrapers/.agent/index.md](../../scrapers/.agent/index.md) | FastAPI scrape jobs, Celery, Playwright, cache, `cdp_scraper` receiver | `make -C scrapers test lint` |
| API Diversos | `muvstok-api/` | [muvstok-api/AGENTS.md](../../muvstok-api/AGENTS.md) -> [muvstok-api/.agent/index.md](../../muvstok-api/.agent/index.md) | Muvstok jobs, Redis Streams worker, PostgreSQL ingestion, `cdp_stokapi` receiver | `make check-muvstok`; service `uv` checks |

## Runtime Flow

```text
Telegram/Gmail/Schedule
  -> cdp_router (n8n/src)
  -> Scraper API POST /api/v1/jobs
  -> API Diversos POST /api/v1/muvstok/jobs
  -> workers process independently
  -> callbacks to scraper-result and muvstok-result webhooks
  -> sheets + Telegram/email notifications
```

## Boundaries

- n8n dispatch belongs to root platform `.agent`; do not create service-local
  router ownership.
- Scraper deep work belongs to `scrapers/.agent`.
- API Diversos deep work belongs to `muvstok-api/.agent`.
- Cross-service contracts belong to `contracts/` plus the owning service
  Pydantic models.
- Live workflow IDs belong to [docs/n8n/LIVE_WORKFLOWS.md](../../docs/n8n/LIVE_WORKFLOWS.md)
  and [.agent/memory/implementation-state.md](../memory/implementation-state.md).

## Naming

- "Scraper" means the public site scraping service in `scrapers/`.
- "API Diversos" is the user-facing name for `muvstok-api/`.
- "StokAPI" may still appear in internal file names, routes, tables, and
  workflow IDs.

## Delegation

| Surface | Platform brief | Service brief |
|---------|----------------|---------------|
| n8n | [.agent/sub-agents/n8n-workflow.md](../sub-agents/n8n-workflow.md) | Platform-owned via [n8n/AGENTS.md](../../n8n/AGENTS.md) |
| Scraper | [.agent/sub-agents/scraper-specialist.md](../sub-agents/scraper-specialist.md) | [scrapers/.agent/sub-agents/](../../scrapers/.agent/sub-agents/) |
| API Diversos | [.agent/sub-agents/api-diversos-specialist.md](../sub-agents/api-diversos-specialist.md) | [muvstok-api/.agent/sub-agents/](../../muvstok-api/.agent/sub-agents/) |
