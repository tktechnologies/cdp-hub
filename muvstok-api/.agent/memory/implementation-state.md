# Implementation State

Last reviewed: 2026-05-27.

## n8n (renamed)

| Workflow | ID | Role |
|----------|-----|------|
| `cdp_router` | `6id6dkinK9xTLfsb` | `.analisar` / `.sku` → Scraper + StokAPI inline |
| `cdp_scraper` | `VfBSV3WU6on8BXm8` | Webhook `scraper-result` |
| `cdp_stokapi` | `t160mzGPYYlJcrjZ` | Webhook `muvstok-result` |

Legacy `cdp_muvstok-api_starter` (`PXLHDzRbBVgs8Xl2`) — deprecated; dispatch only via router.

Sync: monorepo `make sync-n8n` with user approval; includes `cdp_progress` when `CDP_PROGRESS_WORKFLOW_ID` is set.

## Router behaviour

- Shared Code sources: `cdp-app/n8n/src/`
- Scraper anti-bot: **Redis scrape cache 24h** (`SCRAPE_CACHE_TTL_SECONDS=86400`) + PG fallback; router sends `force_refresh: false`
- `.sku` and `.analisar` both run dual pipeline
- Job metadata: `batch_group_id`, `command_route`, `pipeline`

## Duplicate SKUs + per-SKU cache (2026-05-29)

- **Contract change:** ingestion no longer dedups SKUs (`requests.normalize_skus` keeps duplicates + order). A job with N input SKUs stores N `muvstok_job_items` and returns **N callback results**. The `(job_id, sku)` unique constraint was dropped (migration `20260529_0004_drop_job_items_sku_unique`).
- **No re-request for duplicates:** `SkuProcessor` keeps a job-scoped in-memory memo so a duplicate SKU reuses the first occurrence's rows (no second upstream call). A new Redis cache (`app/services/sku_cache.py`, prefix `muvstok:sku:v1:`, 24h success / 6h not_found TTL, `MUVSTOK_CACHE_*`) additionally serves the same SKU across jobs within the window. Cache is best-effort (errors → miss). Failures are never cached.
- `submitted_sku_count` = N (was unique count); callback `items`/`results` length = N; governance counts stay consistent.
- n8n receiver unchanged: `cdp_stokapi` still fans out by `row_number` (maps each unique SKU result to all duplicate sheet rows). Telegram/Historico counts now match the scraper (e.g. 95/95).
- Tests: `tests/test_workers/test_sku_processor_cache.py`, `tests/test_services/test_sku_cache.py`, `tests/test_services/test_request_skus.py`.
- **Deployed 2026-05-29:** migration `20260529_0004` on prod PG; images `20260529-1040` on `cdp-muv-api` / `cdp-muv-worker` with `MUVSTOK_CACHE_*` env.

## API / worker

- FastAPI + worker on Azure `cdp-muv-api` / `cdp-muv-worker`
- **Deploy fix (2026-05-26):** `deploy_muv_worker.sh` had been pushing `Dockerfile.worker` to both apps; API was crash-looping (320+ restarts). Use `scripts/deploy_muv_api.sh` (uvicorn / `Dockerfile.api`) for API and worker script only for `cdp-muv-worker`. Live API revision `cdp-muv-api--0000008` image `20260526-1220`.
- Callbacks to `muvstok-result` with `x-webhook-secret`
- **Progress:** `GET /api/v1/muvstok/jobs/{id}` returns live `items_processed` / `progress_pct` while status is `processing` (read-time recount from DB).
- **User-facing branding** (Telegram, Sheets, n8n node labels, `app_name`): **API Diversos** / `api-diversos`. Internal routes, env vars, DB tables, and webhook path unchanged for compatibility.

## Docs

- Platform: `cdp-app/docs/architecture/DUAL_PIPELINE.md`
- Live IDs: `cdp-app/docs/n8n/LIVE_WORKFLOWS.md`
