# Command: Add Or Update Tests

## Steps

1. Read source under test and nearby tests.
2. Match existing test style.
3. Prefer pure parsing/unit tests for scraper logic.
4. Mock Playwright in unit tests; real browser only for explicit integration.
5. Cover: success, empty/no-result, malformed data, business rules.
6. Run narrow test file, then shared tests if affected.

## Targets

```bash
uv run pytest tests/test_scrapers -v
uv run pytest tests/test_api -v
uv run pytest tests/test_services/test_orchestrator.py -v
```

## Required Business Coverage

- SKU normalization and exact match
- Mercedes EU transform
- Mercado Livre new-only filtering
- Price parsing per currency/source
- API auth and validation
- Database persistence for job/result changes
