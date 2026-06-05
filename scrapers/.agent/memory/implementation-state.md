# Scraper implementation state

Last reviewed: 2026-06-03. **Handoff source of truth:** `docs/MAINTENANCE_CHECKPOINT.md`.

## Stack

- FastAPI + Celery + Playwright + PostgreSQL
- Redis DB 0: Celery broker; DB 1: scrape cache (24h TTL)
- Production: `cdp-scrapers-api-prod`, `cdp-scrapers-worker-prod`

## n8n (monorepo `n8n/workflows/`)

| Workflow | ID | File |
|----------|-----|------|
| `cdp_router` | `6id6dkinK9xTLfsb` | `n8n/workflows/cdp_router.json` |
| `cdp_scraper` | `VfBSV3WU6on8BXm8` | `n8n/workflows/cdp_scraper.json` |
| `cdp_progress` | `CDP_PROGRESS_WORKFLOW_ID` | `n8n/workflows/cdp_progress.json` |

Router Code source: monorepo `n8n/src/` (not `n8n/shared/dual_dispatch/`).

## Progress visibility (2026-05-27)

- Alembic `8a3c1e95f2b0`: `dispatch_runs` table; job columns `items_processed`, `progress_pct`.
- API: `/api/v1/dispatch-runs` (upsert, list active, for-chat lookup, PATCH progress state).
- `GET /api/v1/jobs/{id}` returns live counters while `running`.
- Run `make migrate` before production deploy.

## Active scrapers

`gm`, `ml`, `vw`, `eu`, `pecadireta`; `melibox` optional in router via `CDP_SCRAPER_SITES`.

**Archived** (code only, not in `SCRAPER_REGISTRY`): `goparts`, `procurapecas`, `ebay`. Re-enable only after proxy site smoke — see `.agent/workflows/proxy-rollout.md`.

## Proxy (2026-06-02)

| Item | Status |
|------|--------|
| Code (`proxy_manager`, `BaseScraper`, circuit breaker) | Ready |
| Spec | `docs/SPECS/PROXY_ROTATION_SPEC.md` |
| Readiness script | `scripts/proxy_readiness_check.py` |
| Site smoke script | `scripts/proxy_site_smoke.py` |
| Production `PROXY_URLS` | **Not confirmed** — set in Key Vault before fail-closed deploy |

## Dual pipeline

Router dispatches Scraper + StokAPI in parallel. Scraper arm uses `force_refresh: false`. Platform doc: `docs/architecture/DUAL_PIPELINE.md`.

## Result semantics (2026-06-03)

- Callback/reporting fields: `sku_result`, `source_health`, `has_valid_price`.
- Seller fields: `seller_uf`, `seller_company_name`, `seller_cnpj`; receiver
  output columns are `uf`, `empresa`, `cnpj` after `vendedor`.
- `FOUND_PRICE` requires exact SKU match plus positive usable price.
- `NO_PRICE`, `NOT_FOUND`, `BLOCKED`, `TIMEOUT`, `ERROR`, and `NOT_QUERIED`
  are not found-price successes.
- Mercado Livre captcha/anti-bot/403/access-denied pages should be emitted as
  `BLOCKED`, not `NOT_FOUND`.

## Before deploy

Verify image tags in Azure. If enabling proxy: run readiness + site smoke; document provider name (no secrets) here and in platform memory.
