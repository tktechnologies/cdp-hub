# Skill: Implement Or Improve A Scraper

Use when adding a new supplier scraper or improving an existing one.

## Read First

1. `src/scrapers/base.py` — lifecycle and shared behavior
2. `src/models/schemas.py` — result contracts
3. `src/scrapers/__init__.py` — registry
4. Closest existing scraper implementation

## Workflow

1. Determine: API vs browser scraping.
2. Implement parsing helpers as small pure functions.
3. Keep browser automation resilient: stable selectors, meaningful waits, no fixed sleeps except throttling.
4. Credentials in `src/config.py`, never inline.
5. Return complete `PartResult` objects.
6. Apply business rules: exact SKU match, ML new-only, Mercedes EU transform, correct currency/origin.
7. Register in `SCRAPER_REGISTRY` only when production-ready.
8. Add tests: success, no result, failure/edge paths.

## Tests

```bash
uv run pytest tests/test_scrapers/test_<site>.py -v
uv run pytest tests/test_scrapers/test_registry.py -v
```

## Done When

- Scraper returns `success`, `not_found`, and `error` consistently.
- Exact match tested.
- Credentials configured through settings.
- Registry and default site lists correct.
