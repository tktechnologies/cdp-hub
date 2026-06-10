# Implementation State

**Last reviewed:** 2026-06-09

> **Live n8n workflow IDs and cross-service deploy facts:** root [`.agent/memory/implementation-state.md`](../../../.agent/memory/implementation-state.md) and [`docs/n8n/LIVE_WORKFLOWS.md`](../../../docs/n8n/LIVE_WORKFLOWS.md). Do not duplicate IDs in this file.

## n8n (this service)

- **Owns:** `n8n/workflows/cdp_stokapi.json`, webhook `muvstok-result`
- **Shares:** production dispatch inline in `cdp_router` via `n8n/src/router_stokapi.js` (platform-owned)
- **Boundaries:** [boundaries/n8n.md](../boundaries/n8n.md) → root [`.agent/boundaries/n8n.md`](../../../.agent/boundaries/n8n.md)
- Legacy `cdp_muvstok-api_starter` (`PXLHDzRbBVgs8Xl2`) — deprecated; dispatch only via router
- Sync: monorepo `make sync-n8n` with user approval

## Duplicate SKUs + per-SKU cache (2026-05-29)

- **Contract change:** ingestion no longer dedups SKUs (`requests.normalize_skus` keeps duplicates + order). A job with N input SKUs stores N `muvstok_job_items` and returns **N callback results**. The `(job_id, sku)` unique constraint was dropped (migration `20260529_0004_drop_job_items_sku_unique`).
- **No re-request for duplicates:** `SkuProcessor` keeps a job-scoped in-memory memo so a duplicate SKU reuses the first occurrence's rows (no second upstream call). A new Redis cache (`app/services/sku_cache.py`, prefix `muvstok:sku:v1:`, 24h success / 6h not_found TTL, `MUVSTOK_CACHE_*`) additionally serves the same SKU across jobs within the window. Cache is best-effort (errors → miss). Failures are never cached.
- `submitted_sku_count` = N (was unique count); callback `items`/`results` length = N; governance counts stay consistent.
- n8n receiver unchanged: `cdp_stokapi` still fans out by `row_number` (maps each unique SKU result to all duplicate sheet rows). Telegram/Historico counts now match the scraper (e.g. 95/95).
- Tests: `tests/test_workers/test_sku_processor_cache.py`, `tests/test_services/test_sku_cache.py`, `tests/test_services/test_request_skus.py`.
- **Deployed 2026-05-29:** migration `20260529_0004` on prod PG; images `20260529-1040` on `cdp-muv-api` / `cdp-muv-worker` with `MUVSTOK_CACHE_*` env.

## Result semantics

Worker `status=succeeded` means lookup completed — not a found-price signal. Canonical callback/Sheets semantics: [`.agent/rules/google-sheets.md`](../../../.agent/rules/google-sheets.md). Detalhado seller columns: `vendedor`, `uf`, `empresa`, `cnpj`; raw `estado` aliases normalize to `uf`.

## API / worker

- FastAPI + worker on Azure `cdp-muv-api` / `cdp-muv-worker`
- **Deploy fix (2026-05-26):** `deploy_muv_worker.sh` had been pushing `Dockerfile.worker` to both apps; API was crash-looping (320+ restarts). Use `scripts/deploy_muv_api.sh` (uvicorn / `Dockerfile.api`) for API and worker script only for `cdp-muv-worker`. Live API revision `cdp-muv-api--0000008` image `20260526-1220`.
- Callbacks to `muvstok-result` with `x-webhook-secret`
- **Progress:** `GET /api/v1/muvstok/jobs/{id}` returns live `items_processed` / `progress_pct` while status is `processing` (read-time recount from DB).
- **User-facing branding** (Telegram, Sheets, n8n node labels, `app_name`): **API Diversos** / `api-diversos`. Internal routes, env vars, DB tables, and webhook path unchanged for compatibility.

## Docs

- Platform dual pipeline: `cdp-app/docs/architecture/DUAL_PIPELINE.md`
- Receiver guide: `muvstok-api/n8n/docs/MUVSTOK_N8N_WORKFLOW_GUIDE.md`
