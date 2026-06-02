# API Cache Agent

## Ownership

Scraper API routes, job orchestration, scrape cache behavior, database models,
and callback request construction.

## Read First

- [../skills/api-endpoint/SKILL.md](../skills/api-endpoint/SKILL.md)
- `src/models/schemas.py`
- `src/services/orchestrator.py`
- `src/services/scrape_cache.py`
- `docs/SPECS/SCRAPE_CACHE_SPEC.md`

## Expected Output

- API/schema/cache behavior summary.
- Migration or contract impact if any.
- Tests run for API, services, and contracts.

## Boundaries

Do not add Muvstok/API Diversos logic here. Cross-service contract changes must
also update root `contracts/` and platform docs.
