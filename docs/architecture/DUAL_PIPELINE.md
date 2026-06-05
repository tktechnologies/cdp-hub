# CDP dual pipeline — Router + Scraper + StokAPI

**Updated:** 2026-06-03

## Workflows

| Workflow | ID | Role |
|----------|-----|------|
| **cdp_router** | `6id6dkinK9xTLfsb` | `.analisar` / `.sku` / `.status` → POST Scraper + StokAPI |
| **cdp_scraper** | `VfBSV3WU6on8BXm8` | Webhook `scraper-result` |
| **cdp_stokapi** | `t160mzGPYYlJcrjZ` | Webhook `muvstok-result` |
| **cdp_progress** | _(import)_ | Scheduled proactive progress (Telegram) |

Router dispatch uses n8n HTTP Request nodes for both background APIs. Code nodes
prepare payloads only; n8n Code nodes must not make outbound HTTP requests.
Scraper and API Diversos jobs are correlated by `batch_group_id`.

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

## Unique dispatch + duplicate sheet rows (2026-06-03)

Router DQ normalizes and deduplicates valid SKUs before dispatch. `skus` is the
unique dispatch list; `sheet_rows` preserves every valid source row with
`row_number`, so duplicate `CODIGO` rows can still be marked/updated.

- **Scraper:** receives unique SKUs; 24h Redis/PostgreSQL cache still applies per
  SKU + site.
- **API Diversos:** receives unique SKUs; the worker still has in-job/Redis
  per-SKU cache (`muvstok:sku:v1:`, `MUVSTOK_CACHE_TTL_SECONDS=86400` success /
  6h not_found).

Sheet writeback (`cdp_stokapi` / `cdp_scraper`) maps each unique SKU result to **all** duplicate `CODIGO` rows by `row_number`.

## Result semantics (Sheets and notifications)

Both receiver callbacks preserve real result meaning:

- `sku_result` / `status_resultado`: `FOUND_PRICE`, `NO_PRICE`, `NOT_FOUND`,
  `BLOCKED`, `TIMEOUT`, `ERROR`, `NOT_QUERIED`.
- `source_health`: `WORKING`, `BLOCKED`, `TIMEOUT`, `ERROR`, `NOT_QUERIED`.
- `has_valid_price`: true only for a usable positive price.
- `Detalhado` seller columns: `vendedor`, `uf`, `empresa`, `cnpj`. `uf` is the
  canonical two-letter Brazilian state output; raw `estado` aliases normalize to
  `uf` and are not written as a sheet column.

Dashboards, Telegram/email summaries, and pivots count “found” only from
`FOUND_PRICE` + `has_valid_price=true`. A row in `Detalhado` is not success by
itself. Blocked/captcha/403 outcomes, including Mercado Livre protection pages,
must remain `BLOCKED` and must not be collapsed into `NOT_FOUND`.

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
