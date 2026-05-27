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

## Scope

- FastAPI `/api/v1/*`, Celery workers, Playwright scrapers, scrape cache, PostgreSQL.
- n8n: `cdp_scraper` receiver; router Code in monorepo `n8n/src/`.

## Quality gates

```bash
make test lint
make migrate   # if schema changed
```

## n8n

- Receiver JSON: `../../n8n/workflows/cdp_scraper.json`
- Router sync: from monorepo root, `make sync-n8n` (platform skill)
- Never publish without user approval
