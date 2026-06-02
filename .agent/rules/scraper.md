# Scraper Service Rules

**Applies to:** `scrapers/**`.

Entry: [scrapers/AGENTS.md](../../scrapers/AGENTS.md) -> [scrapers/.agent/index.md](../../scrapers/.agent/index.md).

## Stack

FastAPI, Playwright, Celery, PostgreSQL, Redis (DB 0 queue, DB 1 cache).

## Conventions

- Active sites: `gm`, `ml`, `vw`, `eu`, `pecadireta`; `melibox` optional.
- Router always sends `force_refresh: false`; cache lives in the worker with a 24h TTL.
- New scrapers extend `BaseScraper` in `scrapers/src/scrapers/base.py`.
- Run `make -C scrapers test lint` before marking scraper work done.

## Out of scope

StokAPI routes, Redis Streams worker, and `cdp_stokapi.json` receiver logic.
