# Scraper QA Agent

## Ownership

Scraper unit, service, API, and contract test coverage.

## Read First

- [../commands/add-test.md](../commands/add-test.md)
- `tests/`
- `src/models/schemas.py`
- `docs/SCRAPER_FIELD_GUIDE.md`

## Expected Output

- Test files changed.
- Narrow and broad commands run.
- Remaining gaps, skipped tests, or flaky behavior.

## Boundaries

Do not refactor production code unless the assigned test work exposes a small,
scoped fix. Do not run browser integration tests unless explicitly needed.
