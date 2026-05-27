# Scraper implementation state

Last reviewed: 2026-05-27. **Handoff source of truth:** `docs/MAINTENANCE_CHECKPOINT.md`.

## Stack

- FastAPI + Celery + Playwright + PostgreSQL
- Redis DB 0: Celery broker; DB 1: scrape cache (24h TTL)
- Production: `cdp-scrapers-api-prod`, `cdp-scrapers-worker-prod`

## n8n (this repo)

| Workflow | ID | File |
|----------|-----|------|
| `cdp_router` | `6id6dkinK9xTLfsb` | `../../n8n/workflows/cdp_router.json` |
| `cdp_scraper` | `VfBSV3WU6on8BXm8` | `../../n8n/workflows/cdp_scraper.json` |
| `cdp_progress` | _(import)_ | `../../n8n/workflows/cdp_progress.json` |

Router Code source: monorepo `n8n/src/` (not `n8n/shared/dual_dispatch/`).

## Progress visibility (2026-05-27)

- Alembic `8a3c1e95f2b0`: `dispatch_runs` table; job columns `items_processed`, `progress_pct`.
- API: `/api/v1/dispatch-runs` (upsert, list active, for-chat lookup, PATCH progress state).
- `GET /api/v1/jobs/{id}` returns live counters while `running`.
- Run `make migrate` (or `uv run alembic upgrade head`) before production deploy.

## Active scrapers

`gm`, `ml`, `vw`, `eu`, `pecadireta`; `melibox` optional. Archived: `goparts`, `procurapecas`, `ebay`.

## Dual pipeline

Router dispatches Scraper + StokAPI in parallel. Scraper arm uses `force_refresh: false`. Platform doc: `../../docs/architecture/DUAL_PIPELINE.md`.

## Before deploy

Verify image tags in Azure — README tags may lag `MAINTENANCE_CHECKPOINT.md`.
