# Skill: Debug A Scraper Failure

Use when a site returns no results, wrong results, auth failures, timeouts, or inconsistent prices.

## Workflow

1. Identify: failing site, SKU, brand, environment, mock mode on/off.
2. Read the scraper implementation + tests.
3. Classify failure:
   - Authentication / session state
   - Selector / page structure drift
   - SKU normalization / exact-match filtering
   - Price / condition / origin parsing
   - Rate limiting / CAPTCHA / bot detection / timeout
4. Fix the smallest layer that owns the bug.
5. Add a regression test.
6. Run narrow tests, then broaden if shared behavior changed.

## Commands

```bash
uv run pytest tests/test_scrapers -v
uv run pytest tests/test_services/test_orchestrator.py -v
PLAYWRIGHT_HEADLESS=false uv run uvicorn src.main:app --reload
```

## Safety

- Never log credentials, cookies, or auth headers.
- Never commit authenticated screenshots.
- Never weaken exact-match filtering to fix a flaky scraper.
