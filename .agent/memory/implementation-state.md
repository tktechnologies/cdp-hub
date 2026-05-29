# CDP Platform — Implementation State

Last reviewed: 2026-05-27.

## n8n (live)

| Workflow | ID | Webhook / trigger |
|----------|-----|-------------------|
| `cdp_router` | `6id6dkinK9xTLfsb` | Telegram, Gmail, schedule |
| `cdp_scraper` | `VfBSV3WU6on8BXm8` | `scraper-result` |
| `cdp_stokapi` | `t160mzGPYYlJcrjZ` | `muvstok-result` |
| `cdp_progress` | _(not yet live — import JSON)_ | Schedule (`CDP_PROGRESS_INTERVAL_MIN`) |

Sync: `make sync-n8n` from monorepo root (pushes router + receivers; `cdp_progress` is local JSON only until first import/publish in n8n UI).

Last publish: 2026-05-27 14:15 UTC via `make sync-n8n`; router, scraper receiver, and StokAPI receiver validated, updated, and published. `cdp_progress` remained local-only.

Post-deploy audit (2026-05-27 15:25 UTC): `cdp_router`, `cdp_scraper`, and `cdp_stokapi` active via MCP at `https://automacao.tktechnologies.com.br/mcp-server/http`; custom hostname binding restored on `cdp-n8n-prod` with SNI managed certificate.

Ops fix (2026-05-27 17:09 UTC): Telegram `.analisar` failed because HTTP node URL/header expressions read `$env` while n8n blocked env access. Router now resolves API URLs/keys inside shared Code nodes (`$env` first, `process.env` fallback), HTTP nodes read `$json.*`, and `cdp-n8n-prod` explicitly sets `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`; live revision `cdp-n8n-prod--0000016`, router active version `73c60e4c-91cd-4b61-8710-7dec588c6839`. MCP retry execution `609` succeeded; scraper job `a0332b0b-2c42-4c48-9fcc-848e842409c7` and StokAPI job `3f76d662-8911-4bc2-aa41-38a0874798db` were accepted.

Router publish (2026-05-27): duplicate SKUs are now included as real work items in `cdp_router` DQ instead of being skipped; live active router version `031e8d67-32f1-4ec8-a585-1ee970eecab4`.

Duplicate SKU end-to-end (2026-05-29): the desired contract is **N input SKUs → N results, duplicates served from cache, no re-request**. The router already preserves + flags duplicates (`router_dq.js`), and the scraper already returns N results with duplicate rows served from its 24h Redis cache. The gap was **StokAPI**, which deduped at ingestion (93 vs 95) and had no per-SKU cache. Fixed in `muvstok-api`: ingestion keeps duplicates, the `(job_id, sku)` unique constraint was dropped (migration `20260529_0004`), the worker reuses the first occurrence via an in-job memo + a new Redis 24h per-SKU cache (`app/services/sku_cache.py`, `MUVSTOK_CACHE_*`), and the callback now returns N results with `submitted_sku_count=N`. **Deployed 2026-05-29:** migration on `cdp-scrapers-pg-prod`; images `cdp-muv-api:20260529-1040` and `cdp-muv-worker:20260529-1040` with `MUVSTOK_CACHE_ENABLED=true`. Tests: `muvstok-api/tests/` (25 pass).

Duplicate SKU sheet marking fix (2026-05-29): both receivers wrote back to `CDP_SKUs` matching on `CODIGO`, so only the **first** row sharing a SKU was marked — duplicate CODIGO rows stayed blank in PROCESSADO/ENCONTRADO/NOTIFICADO (StokAPI also dedups SKUs at ingestion via `normalize_skus`). Fix: read the `SKUs` sheet, fan out one update per matching `row_number`, and match on `row_number`. StokAPI (`cdp_stokapi`, 17 nodes, active `028f36fd-698b-4d28-9c61-d5c52718df69`) adds `📄 Ler CDP_SKUs (linhas)` → `🧭 Mapear linhas por CODIGO` before `✅ Atualizar CDP_SKUs`. Scraper (`cdp_scraper`, 47 nodes, active `d834d15c-7796-4f9f-be9c-988ab5efafe2`) adds a `🧺 Coletar → 📄 Ler → 🧭 Mapear` trio before each of the 3 markers (ENCONTRADO, NOTIFICADO, Bulk NOTIFICADO). Idempotent patch logic lives in `muvstok-api/scripts/patch_muvstok_receiver_workflow.py` (`patch_rownum_pipeline` + `patch_cdp_skus_node`) and `scrapers/scripts/patch_scraper_receiver_workflow.py` (`patch_rownum_markers`). StokAPI dedup is intentionally kept; row-level fan-out covers duplicate sheet rows.

## Scraper (scrapers/)

- **Stack:** FastAPI + Celery + Playwright + PostgreSQL + Redis (DB 0 queue, DB 1 cache).
- **Azure:** `cdp-scrapers-api-prod`, `cdp-scrapers-worker-prod` in RG `automation`.
- **Last deploy:** 2026-05-27, image `cdpscraperprodacr.azurecr.io/cdp-scraper:latest` (ACR run `ch8`), API revision `cdp-scrapers-api-prod--0000012`, worker revision `cdp-scrapers-worker-prod--0000015`.
- **Cache:** 24h TTL on success/no_price; router always `force_refresh: false`.
- **Active sites:** gm, ml, vw, eu, pecadireta; melibox optional; goparts/procurapecas/ebay archived.
- **Agent docs:** `scrapers/.agent/index.md`, `scrapers/docs/MAINTENANCE_CHECKPOINT.md`.

## StokAPI (muvstok-api/)

- **Stack:** FastAPI + Redis Streams worker (no Celery) + PostgreSQL.
- **Azure:** `cdp-muv-api`, `cdp-muv-worker`.
- **Last deploy:** 2026-05-27, API image `cdpscraperprodacr.azurecr.io/cdp-muv-api:20260527-1205` (revision `cdp-muv-api--0000009`), worker image `cdpscraperprodacr.azurecr.io/cdp-muv-worker:20260527-1208` (revision `cdp-muv-worker--0000010`).
- **Deploy fix (2026-05-26):** use `deploy_muv_api.sh` for API, `deploy_muv_worker.sh` for worker only.
- **Branding:** API Diversos externally; `muvstok` paths/tables unchanged.
- **Agent docs:** `muvstok-api/.agent/memory/implementation-state.md`.

## Shared router + progress

- Source: `n8n/src/` (12 JS files).
- Injected into `n8n/workflows/cdp_router.json` and `cdp_progress.json` via `scripts/sync_workflow_code_from_shared.py`.

## Repo boundary / GitHub (2026-05-27)

- Root `cdp-app` is the canonical monorepo.
- Former nested Git repositories were converted to regular directories:
  - `scrapers/`
  - `muvstok-api/`
- Local-only backup bundle/diff/gitdir location: `.git-boundary-backups/20260527-monorepo-migration/`.
- GitHub push remains blocked until a root remote is chosen and GitHub auth is restored (`gh auth status` reported not logged in).

## Progress visibility (2026-05-27)

- **Scraper API:** incremental `items_processed`, `progress_pct`, `estimated_seconds_remaining` on `GET /api/v1/jobs/{id}` while running; Alembic `8a3c1e95f2b0` adds `dispatch_runs` table + job progress columns.
- **Dispatch runs API** (`X-API-Key`): `POST /api/v1/dispatch-runs`, `GET …/active`, `GET …/active/for-chat/{chat_id}`, `PATCH …/{run_id}`.
- **StokAPI:** live `items_processed` / `progress_pct` on `GET /api/v1/muvstok/jobs/{id}` while `processing` (read-time recount).
- **Router (`cdp_router`):** Telegram `.status`, `.andamento`, `.progresso` → polls both job APIs; after dispatch writes `cdp_active_run` (staticData) + `POST /dispatch-runs`.
- **Proactive workflow:** `n8n/workflows/cdp_progress.json` — schedule polls `GET /dispatch-runs/active`, fetches job status, sends Telegram when thresholds met.
- **Env (n8n):** `CDP_PROGRESS_INTERVAL_MIN=10` (0 = disable), `CDP_PROGRESS_MIN_SKUS=15`, `CDP_PROGRESS_MIN_STEP_PCT=10`, `CDP_PROGRESS_MAX_MESSAGES=6`; uses `CDP_SCRAPER_API_BASE` + scraper `X-API-Key`.

## Known gaps (platform)

- **`make sync-n8n` does NOT apply graph changes (2026-05-29).** `scrapers/scripts/push_workflow_mcp.py` calls `update_workflow` with a `code` argument, but the current MCP `update_workflow` only accepts `operations` (`additionalProperties:false`). The code-based update silently no-ops (`update OK id=None`); `validate_workflow` and `publish_workflow` still report success, so the pipeline *looks* like it worked while the live graph is unchanged. Until `push_workflow_mcp.py` is rewritten to diff→`operations` (or `create_workflow_from_code`), structural workflow changes must be applied via `update_workflow` `operations` + `publish_workflow` (see the 2026-05-29 dup-SKU fix). The repo JSON + patch scripts remain the source of truth.
- `cdp_progress` not in `make sync-n8n` yet — manual import until script updated.
- Legacy `scrapers/n8n/docs/` deprecated; use `docs/n8n/` and `.agent/boundaries/n8n.md`.
- GitHub remote/push is not configured for root monorepo yet; local commit can be created, but remote publication needs `gh auth login` or a repo URL/token.
