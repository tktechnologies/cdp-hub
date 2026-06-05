# Service boundaries

Agents must respect these lines when changing CDP.

## Scraper (`scrapers/`)

**In scope:** FastAPI, Celery, Playwright scrapers, scrape cache (Redis DB 1), PostgreSQL job storage, `cdp_scraper` workflow JSON, scraper n8n docs/settings.

**Out of scope:** API Diversos/StokAPI upstream stock client, Redis Streams job
queue for StokAPI, `cdp_stokapi.json` (except coordinated callback field names
documented at platform level).

**Default sites for jobs:** `gm`, `ml`, `vw`, `eu`, `pecadireta`.

## StokAPI (`muvstok-api/`)

**In scope:** `/api/v1/muvstok/*`, Redis Streams worker, upstream stock client,
PostgreSQL ingestion, `cdp_stokapi` workflow JSON.

**Out of scope:** Playwright, Celery scrape tasks, scrape cache, `cdp_scraper.json`.

**Branding:** User-facing **API Diversos**; keep `muvstok` in routes, tables, env vars, webhook path.

## Platform (`cdp-app/` root)

**In scope:** `n8n/src/`, `scripts/sync-all-n8n.sh`, `docs/architecture/`, `docs/n8n/LIVE_WORKFLOWS.md`, `.agent/` platform layer.

**Out of scope:** Business logic inside `scrapers/src/` or `muvstok-api/app/` — delegate to service agents.

## Shared infrastructure (read-only for most agents)

| Resource | Used by |
|----------|---------|
| `cdp-scrapers-pg-prod` | Scraper (primary); StokAPI may use separate DB locally |
| `cdp-scrapers-redis-prod` DB 0 | Celery |
| Same Redis DB 1 | Scrape cache only |
| StokAPI Redis stream | StokAPI worker only |
| `cdp-n8n-prod` | All three workflows |
| `cdp-scrapers-kv-prod` | API keys, webhook secrets, API base URLs |
