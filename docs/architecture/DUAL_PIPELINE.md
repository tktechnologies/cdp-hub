# CDP dual pipeline — Router + Scraper + StokAPI

**Updated:** 2026-05-27

## Workflows

| Workflow | ID | Role |
|----------|-----|------|
| **cdp_router** | `6id6dkinK9xTLfsb` | `.analisar` / `.sku` / `.status` → POST Scraper + StokAPI |
| **cdp_scraper** | `VfBSV3WU6on8BXm8` | Webhook `scraper-result` |
| **cdp_stokapi** | `t160mzGPYYlJcrjZ` | Webhook `muvstok-result` |
| **cdp_progress** | _(import)_ | Scheduled proactive progress (Telegram) |

## Scraper cache (24h) — anti-bot

Repeat requests for the **same SKU + site** within 24 hours do **not** run Playwright again when `force_refresh=false` (default from router).

| Layer | Technology | TTL |
|-------|------------|-----|
| Hot cache | Redis DB 1 (`SCRAPE_CACHE_REDIS_URL`) | `SCRAPE_CACHE_TTL_SECONDS=86400` (success / no_price) |
| Warm fallback | PostgreSQL latest job rows | Same 24h window |
| Bypass | `force_refresh=true` on API | Live scrape only |

Flow: `POST /api/v1/jobs` → worker `orchestrator._search_sku_all_sites` → cache hit returns stored `SiteResult` (`from_cache=true`, `search_time_ms=0`).

Docs: `scrapers/docs/SPECS/SCRAPE_CACHE_SPEC.md`, `scrapers/docs/SCRAPE_CACHE_OPERATIONS.md`.

**n8n does not pre-filter sites** — every dispatch sends full site list; the API/worker applies cache.

## StokAPI cache (24h) + duplicate SKUs (2026-05-29)

Both pipelines follow the same contract: **N input SKUs → N results, duplicates served from cache (one upstream call per unique SKU).**

- **Scraper:** sequential per-row processing; the 2nd occurrence of a SKU hits the 24h Redis scrape cache.
- **StokAPI:** ingestion keeps duplicates (no dedup); the worker reuses the first occurrence via an in-job memo and a Redis per-SKU cache (`muvstok:sku:v1:`, `MUVSTOK_CACHE_TTL_SECONDS=86400` success / 6h not_found). Returns one callback result per input row.

Sheet writeback (`cdp_stokapi` / `cdp_scraper`) maps each unique SKU result to **all** duplicate `CODIGO` rows by `row_number`.

## Commands

| Command | Scraper | StokAPI | Notes |
|---------|---------|---------|-------|
| `.analisar` | Yes (all unprocessed SKUs from sheet) | Yes (same set) | Dual dispatch |
| `.sku …` | Yes (all listed SKUs) | Yes (same set) | Dual dispatch |
| `.status` / `.andamento` / `.progresso` | Poll job API | Poll job API | On-demand progress; uses `cdp_active_run` or `GET /dispatch-runs/active/for-chat/{chat_id}` |

## Dual-pipeline status

After dispatch, the router registers the run (`POST /api/v1/dispatch-runs`) and stores job IDs in workflow staticData. While jobs run:

- **Scraper** `GET /api/v1/jobs/{id}` — `items_processed`, `progress_pct`, `estimated_seconds_remaining`.
- **StokAPI** `GET /api/v1/muvstok/jobs/{id}` — live item counts and `progress_pct` while `processing`.
- **Proactive updates** — `cdp_progress` polls `GET /dispatch-runs/active` on a schedule (`CDP_PROGRESS_INTERVAL_MIN`, default 10 min).

Env (n8n): `CDP_PROGRESS_INTERVAL_MIN`, `CDP_PROGRESS_MIN_SKUS`, `CDP_PROGRESS_MIN_STEP_PCT`, `CDP_PROGRESS_MAX_MESSAGES`.

## Sync

```bash
cd cdp-app && make sync-n8n
```
