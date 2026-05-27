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

- `cdp_progress` not in `make sync-n8n` yet — manual import until script updated.
- Legacy `scrapers/n8n/docs/` deprecated; use `docs/n8n/` and `.agent/boundaries/n8n.md`.
- GitHub remote/push is not configured for root monorepo yet; local commit can be created, but remote publication needs `gh auth login` or a repo URL/token.
