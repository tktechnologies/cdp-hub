# Command: Implement Or Improve Scraper

Use [../skills/scraper-implementation/SKILL.md](../skills/scraper-implementation/SKILL.md).

## Steps

1. Read `src/scrapers/base.py`, `src/models/schemas.py`, `src/scrapers/__init__.py`, and target scraper.
2. Confirm API vs Playwright approach.
3. Implement/update parsing, login, search, filtering, result mapping.
4. Register in `SCRAPER_REGISTRY` only when production-ready.
5. Add focused tests in `tests/test_scrapers/`.
6. Run narrow tests + registry tests.

## Acceptance

- Exact SKU behavior preserved.
- Result fields complete.
- No credentials or browser states committed.
- Tests cover success, no result, and failure paths.
