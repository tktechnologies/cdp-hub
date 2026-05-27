# Implementation State

Last reviewed: 2026-05-27.

## n8n (renamed)

| Workflow | ID | Role |
|----------|-----|------|
| `cdp_router` | `6id6dkinK9xTLfsb` | `.analisar` / `.sku` → Scraper + StokAPI inline |
| `cdp_scraper` | `VfBSV3WU6on8BXm8` | Webhook `scraper-result` |
| `cdp_stokapi` | `t160mzGPYYlJcrjZ` | Webhook `muvstok-result` |

Legacy `cdp_muvstok-api_starter` (`PXLHDzRbBVgs8Xl2`) — deprecated; dispatch only via router.

Sync: `cdp-app/scripts/sync-all-n8n.sh` or `make -C .. sync-n8n` from monorepo root.

## Router behaviour

- Shared Code sources: `cdp-app/n8n/src/`
- Scraper anti-bot: **Redis scrape cache 24h** (`SCRAPE_CACHE_TTL_SECONDS=86400`) + PG fallback; router sends `force_refresh: false`
- `.sku` and `.analisar` both run dual pipeline
- Job metadata: `batch_group_id`, `command_route`, `pipeline`

## API / worker

- FastAPI + worker on Azure `cdp-muv-api` / `cdp-muv-worker`
- **Deploy fix (2026-05-26):** `deploy_muv_worker.sh` had been pushing `Dockerfile.worker` to both apps; API was crash-looping (320+ restarts). Use `scripts/deploy_muv_api.sh` (uvicorn / `Dockerfile.api`) for API and worker script only for `cdp-muv-worker`. Live API revision `cdp-muv-api--0000008` image `20260526-1220`.
- Callbacks to `muvstok-result` with `x-webhook-secret`
- **Progress:** `GET /api/v1/muvstok/jobs/{id}` returns live `items_processed` / `progress_pct` while status is `processing` (read-time recount from DB).
- **User-facing branding** (Telegram, Sheets, n8n node labels, `app_name`): **API Diversos** / `api-diversos`. Internal routes, env vars, DB tables, and webhook path unchanged for compatibility.

## Docs

- Platform: `cdp-app/docs/architecture/DUAL_PIPELINE.md`
- Live IDs: `cdp-app/docs/n8n/LIVE_WORKFLOWS.md`
