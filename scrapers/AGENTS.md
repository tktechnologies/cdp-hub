# AGENTS.md — CDP Scraper

Instructions for AI agents working on the **scraper service** inside the CDP monorepo.

## Tier

| Tier | Entry |
|------|--------|
| **Platform** (router, dual pipeline, sync all workflows) | [../AGENTS.md](../AGENTS.md) → [../.agent/index.md](../.agent/index.md) |
| **This service** (Playwright, API, Celery, cache) | This file → [.agent/index.md](.agent/index.md) |

Do not edit `n8n/src/` or `muvstok-api/` from scraper-only tasks without reading platform boundaries.

## Read order

1. [.agent/rules.md](.agent/rules.md)
2. [.agent/index.md](.agent/index.md)
3. [.agent/memory/implementation-state.md](.agent/memory/implementation-state.md)
4. [docs/MAINTENANCE_CHECKPOINT.md](docs/MAINTENANCE_CHECKPOINT.md) for production snapshot
5. [../.agent/knowledge/service-catalog.md](../.agent/knowledge/service-catalog.md) when the task crosses n8n or API Diversos boundaries

## Scope

- FastAPI `/api/v1/*`, Celery workers, Playwright scrapers, scrape cache, PostgreSQL.
- n8n: `cdp_scraper` receiver; router Code in monorepo `n8n/src/`.

## Quality gates

```bash
make test lint
make migrate   # if schema changed
```

When changing job/callback JSON shapes, update `../contracts/` and `tests/test_contracts/`.

## n8n

- Receiver JSON: `../../n8n/workflows/cdp_scraper.json`
- Router sync: from monorepo root, `make sync-n8n` (platform skill)
- Never publish without user approval

## Brazilian ISP proxy rollout

Code is ready (`proxy_manager`, `BaseScraper`, `PROXY_ROTATION_SPEC.md`). Production still needs a purchased BR ISP/static residential URL in Key Vault.

| Step | Command / doc |
|------|----------------|
| 0. **IPRoyal purchase + apply** | [docs/runbooks/iproyal-isp-proxy-setup.md](docs/runbooks/iproyal-isp-proxy-setup.md) |
| 1. Readiness (ipify only) | `uv run python scripts/proxy_readiness_check.py --proxy-url '...'` |
| 2. Per-site smoke | `uv run python scripts/proxy_site_smoke.py --from-env` |
| 3. Workflow checklist | [.agent/workflows/proxy-rollout.md](.agent/workflows/proxy-rollout.md) |
| 4. Command reference | [.agent/commands/proxy-readiness.md](.agent/commands/proxy-readiness.md) |

**Archived sites** (`goparts`, `procurapecas`, `ebay`): re-add to `SCRAPER_REGISTRY` only after documented proxy smoke — Cloudflare may still block headless Playwright.

**Melibox:** primary validation target (403 on Azure egress without BR ISP). Router includes `melibox` only via `CDP_SCRAPER_SITES`, not default `gm,ml,vw,eu,pecadireta`.
