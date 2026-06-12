# Scraper implementation state

**Last reviewed:** 2026-06-12 · **Handoff:** `docs/MAINTENANCE_CHECKPOINT.md`

> **Live n8n workflow IDs, deploy tags, and cross-service facts:** root [`.agent/memory/implementation-state.md`](../../../.agent/memory/implementation-state.md) and [`docs/n8n/LIVE_WORKFLOWS.md`](../../../docs/n8n/LIVE_WORKFLOWS.md). Do not duplicate IDs in this file.

## Stack

- FastAPI + Celery + Playwright + PostgreSQL
- Redis DB 0: Celery broker; DB 1: scrape cache (24h TTL for success, no_price, not_found, blocked)
- Production: `cdp-scrapers-api-prod`, `cdp-scrapers-worker-prod`

## n8n (this service)

- **Owns:** `n8n/workflows/cdp_scraper.json`, webhook `scraper-result`
- **Shares:** router JSON at `n8n/workflows/cdp_router.json`; router Code in `n8n/src/` (platform-owned)
- **Boundaries:** [boundaries/n8n.md](../boundaries/n8n.md) → root [`.agent/boundaries/n8n.md`](../../../.agent/boundaries/n8n.md)

## Progress visibility (2026-05-27)

- Alembic `8a3c1e95f2b0`: `dispatch_runs` table; job columns `items_processed`, `progress_pct`.
- API: `/api/v1/dispatch-runs` (upsert, list active, for-chat lookup, PATCH progress state).
- `GET /api/v1/jobs/{id}` returns live counters while `running`.
- Run `make migrate` before production deploy.

## Active scrapers

`gm`, `ml`, `vw`, `eu`, `melibox` via live `CDP_SCRAPER_SITES`.

**Disabled pending smoke:** `pecadireta` (cached HTTP 403 anti-bot blocks on
2026-06-09). **Archived** (code only, not in `SCRAPER_REGISTRY`): `goparts`,
`procurapecas`, `ebay`. Re-enable only after fresh proxy site smoke — see
`.agent/workflows/proxy-rollout.md`.

## Proxy (2026-06-09)

| Item | Status |
|------|--------|
| Provider | **IPRoyal ISP BR** — 2 dedicated IPs (HTTP port 12323) |
| Code (`proxy_manager`, `BaseScraper`, circuit breaker) | Ready |
| Spec | `docs/SPECS/PROXY_ROTATION_SPEC.md` |
| Readiness script | `scripts/proxy_readiness_check.py` |
| Site smoke script | `scripts/proxy_site_smoke.py` |
| Local validation | **Passed 2026-06-09** — both IPs; Playwright egress OK |
| Local site smoke | **Melibox PASS** (18 priced); gm/vw/ml `not_found`; pecadireta/eu previously passed locally but prod cache showed HTTP 403 anti-bot blocks on 2026-06-09; keep disabled until fresh smoke |
| Production `PROXY_URLS` | **Applied on Container Apps** 2026-06-09 (`configure-iproyal-proxy-prod.sh`); Key Vault write blocked for current `az` user — persist manually |
| Azure egress whitelist | **Done** — `172.193.112.98` whitelisted in IPRoyal (2026-06-09) |
| Production Melibox smoke | **PASS** — job `d4c9bec0-426d-4c1a-9ae2-8ba124f90b56`, 18 priced rows |

## Dual pipeline

Router dispatches Scraper + StokAPI in parallel. Scraper arm uses `force_refresh: false`. Platform: [`docs/architecture/DUAL_PIPELINE.md`](../../../docs/architecture/DUAL_PIPELINE.md).

## Cache policy (2026-06-12)

To reduce anti-bot pressure, cacheable per-site statuses now all hold for 24h:
`success`, `no_price`, `not_found`, and `blocked`. `error` and `timeout`
remain uncached. STOKAI live API/worker revisions `0000003` were updated with
`SCRAPE_CACHE_TTL_NOT_FOUND_SECONDS=86400` and
`SCRAPE_CACHE_TTL_BLOCKED_SECONDS=86400`; repeat lookup for email SKU
`5U6959775` returned `cache_hits=5`, `live_scrapes=0`.

## Reporting (callback fields)

Canonical semantics: [`.agent/rules/google-sheets.md`](../../../.agent/rules/google-sheets.md). Scraper payload: `sku_result`, `source_health`, `has_valid_price`; seller fields `seller_uf`, `seller_company_name`, `seller_cnpj` → receiver columns `uf`, `empresa`, `cnpj`.

## Before deploy

Verify image tags in Azure (see platform memory). If enabling proxy: run readiness + site smoke; document provider name (no secrets) here and in platform memory.
