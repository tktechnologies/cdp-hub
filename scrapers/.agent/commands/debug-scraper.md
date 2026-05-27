# Command: Debug Scraper

Use [../skills/scraper-debugging/SKILL.md](../skills/scraper-debugging/SKILL.md).

## Quick Triage

1. Identify failing site, SKU, brand, endpoint/job.
2. Check mock mode status.
3. Read failing scraper + tests.
4. Classify: auth, selector drift, parsing, exact match, timeout, rate limit, callback.
5. Fix the smallest layer.
6. Add regression test.

## Commands

```bash
uv run pytest tests/test_scrapers -v
PLAYWRIGHT_HEADLESS=false uv run uvicorn src.main:app --reload
```

## Safety

Never commit `browser_states/`, authenticated screenshots, `.env`, or secrets in logs.
