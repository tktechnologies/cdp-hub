# Local Validation Runbook

Use this before any Azure deployment.

## 1. Configure Environment

Copy `.env.example` to `.env` and set real values. Required local gates:

```bash
DATABASE_URL=postgresql+asyncpg://cdp:cdp_pass@localhost:5432/cdp_scraper
DATABASE_URL_SYNC=postgresql://cdp:cdp_pass@localhost:5432/cdp_scraper
REDIS_URL=redis://localhost:6379/0
JOB_EXECUTION_BACKEND=local
MOCK_SCRAPERS=false
PROXY_ROTATION_ENABLED=false
PLAYWRIGHT_HEADLESS=false
PLAYWRIGHT_SLOW_MO_MS=250
```

If another local project already owns port `6379`, set `REDIS_HOST_PORT` and `REDIS_URL`
to the same alternate host port, for example `6381`.

GM uses the public Peça Chevrolet flow. `MockGMScraper` is used only when
`MOCK_SCRAPERS=true`.

## 2. Reset Local Database

This intentionally removes local Docker volumes:

```bash
make local-db-reset
```

## 3. Start API

```bash
make dev
```

For a production-like local queue check, set `JOB_EXECUTION_BACKEND=celery`,
start the API with `make dev`, and run a second terminal with:

```bash
make worker
```

Confirm:

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/
curl http://localhost:8000/metrics
```

## 4. Prepare Price Manifest

Copy the example manifest and replace every placeholder with manually verified values:

```bash
cp docs/validation/local_scraper_manifest.example.json docs/validation/local_scraper_manifest.local.json
```

The local file is gitignored because it may contain customer SKUs or source evidence.

## 5. Run Validation

```bash
make validate-local-preflight
MANIFEST=docs/validation/local_scraper_manifest.local.json make validate-local-scrapers
```

The scraper validator submits real API jobs, polls completion, verifies price/currency/SKU rules, and confirms persistence in `scrape_jobs`, `scrape_items`, and `part_results`.

Azure work stays blocked until this run passes for all required sites.

## 6. Headed One-Case Scraper Checks

Use this when you need to watch a scraper in a visible browser:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py \
  --site ml \
  --sku 06K907811B \
  --brand VW \
  --timeout-seconds 120 \
  --slow-mo-ms 250 \
  --hold-seconds 3
```

The full manual runbook is `docs/SCRAPER_MANUAL_VALIDATION.md`.
