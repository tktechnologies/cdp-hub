# StokAPI Rules

**Applies to:** `muvstok-api/**`.

Entry: [muvstok-api/AGENTS.md](../../muvstok-api/AGENTS.md) -> [muvstok-api/.agent/index.md](../../muvstok-api/.agent/index.md).

## Stack

FastAPI, Redis Streams worker, PostgreSQL, Azure Key Vault.

## Conventions

- Dependency direction: route/worker -> service -> repository/client.
- Keep `muvstok` in routes, tables, and env vars; user-facing name is API Diversos.
- Run `make check-muvstok` or `cd muvstok-api && uv run ruff check . && uv run mypy .`.

## Out of scope

Playwright, Celery scrape tasks, scrape cache, and `cdp_scraper.json`.
