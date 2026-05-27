# quality-gates

**Purpose:** Run lint and tests for both services.

```bash
make lint-all
make test-all
make check-specs
```

**Scraper only:** `make -C scrapers test lint`

**StokAPI only:** `cd muvstok-api && uv run ruff check . && uv run mypy .`
