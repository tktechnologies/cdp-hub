# CDP Parts Scraper

FastAPI and Playwright service for automotive parts price lookup across supplier sites. It accepts SKU jobs, searches configured sources, normalizes results, persists job data, and exposes JSON responses for CDP and external automation.

**New maintenance agent?** Start with [`docs/MAINTENANCE_CHECKPOINT.md`](docs/MAINTENANCE_CHECKPOINT.md).

## Scope

This repository is focused on the scraper service only:
- Generic API endpoints and callback delivery.
- Scraper implementations.
- Job orchestration, Celery/Redis queue execution, and persistence.
- Tests, migrations, deployment scripts, and scraper operating docs.

Presentation demos, video-analysis artifacts, generic automation experiments, and unrelated application code should stay out of this repo.

## Supported Sites

Supported site IDs are defined in `src/models/schemas.py` and registered in `src/scrapers/__init__.py`:

- `gm`
- `ml`
- `vw`
- `eu`
- `pecadireta`
- `melibox`

`MockGMScraper` supports local/integration testing when `MOCK_SCRAPERS=true`.
`goparts`, **Procura Peças** (`procurapecas`), and **eBay** (`ebay`) are archived:
code and docs remain for reference, but they are not in the active registry or
default API job sites. The local demo scripts can still run them explicitly for
manual all-source checks.

## Production Status

**Handoff snapshot:** `docs/MAINTENANCE_CHECKPOINT.md` (2026-05-21)

Production images (verify in Azure before deploy):

```text
API:    cdpscraperprodacr.azurecr.io/cdp-scraper:lookup-direct-20260521-1439
Worker: cdpscraperprodacr.azurecr.io/cdp-scraper:scrape-cache-ssl-20260521-1402
```

Live Azure resources in `automation`:
- API: `cdp-scrapers-api-prod`
- Worker: `cdp-scrapers-worker-prod`
- N8N: `cdp-n8n-prod` — `https://automacao.tktechnologies.com.br`
- PostgreSQL: `cdp-scrapers-pg-prod`
- Redis: `cdp-scrapers-redis-prod` (DB 0 Celery, DB 1 scrape cache)
- Key Vault: `cdp-scrapers-kv-prod`
- ACR: `cdpscraperprodacr`

Latest validation artifacts:
- `docs/validation/latest_production_curl_smoke.json` (fixed SKU smoke)
- `docs/validation/latest_production_5sku_cache_audit.json` (`/lookup` cache)
- `docs/validation/latest_production_5sku_jobs_cache_audit.json` (`/jobs` cache)
- `docs/validation/latest_5sku_e2e_20260521.md` (batch E2E)

Summary:
- Scrape cache: **PASS** on `/lookup` and `/jobs` (5-SKU audits).
- Scraper prices: GM, Peça Direta, EU, VW OK; ML smoke SKU stale; Melibox blocked.
- n8n automated callbacks: **blocked** until webhook secret strip is deployed.
- Live n8n workflows: drift from repo — see `n8n/docs/AUDIT_2026-05-21.md`.

## Quick Start

```bash
make setup
cp -n .env.example .env
make migrate
make dev
```

For credential-free local testing:

```bash
MOCK_SCRAPERS=true make dev
```

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/jobs` | `X-API-Key` | Submit a batch scraping job |
| `POST` | `/api/v1/demo/telegram` | `X-API-Key` | Submit a small demo job and route completion to Telegram via n8n |
| `POST` | `/api/v1/demo/interview` | `X-API-Key` | Start the local `make interview-demo` style browser demo |
| `GET` | `/api/v1/demo/interview/{id}` | `X-API-Key` | Poll local interview demo status and final summary |
| `GET` | `/api/v1/jobs/{id}` | `X-API-Key` | Get job status and results |
| `POST` | `/api/v1/lookup` | `X-API-Key` | Synchronous single-SKU lookup (uses 24h Redis cache per site unless `force_refresh`) |
| `GET` | `/api/v1/health` | None | Health check |

OpenAPI docs are available at `http://localhost:8000/docs` when the API is running.

### Scrape cache (24h Redis)

Per-site SKU results are cached in Redis (DB **1**) to reduce repeat Playwright
traffic. See `docs/SPECS/SCRAPE_CACHE_SPEC.md` and `docs/SCRAPE_CACHE_OPERATIONS.md`.

```bash
make local-db-up
make dev
make smoke-scrape-cache-local   # requires API_KEY in env or .env
```

Fresh agent session: read `.agent/prompts/agent-startup.md`.

Jobs may include `callback_url`; when the job finishes, the service POSTs the
result payload to that URL with `X-Webhook-Secret: CALLBACK_WEBHOOK_SECRET`.
External automation systems should call `POST /api/v1/jobs` instead of relying
on tool-specific inbound webhook routes.

Local Telegram demo:

```bash
curl -X POST http://localhost:8000/api/v1/demo/telegram \
  -H "X-API-Key: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "YOUR_TELEGRAM_CHAT_ID",
    "items": [{"sku": "06K907811B", "brand": "VW"}],
    "sites": ["gm", "vw"]
  }'
```

The endpoint uses `DEMO_CALLBACK_URL` when set, otherwise the production n8n
receiver at `https://automacao.tktechnologies.com.br/webhook/scraper-result`.

Browser demo (headed, all active scrapers):

```bash
make demo
```

## Queue Execution

Development defaults to `JOB_EXECUTION_BACKEND=local`, which runs jobs inside
the API process for fast feedback. Production should use
`JOB_EXECUTION_BACKEND=celery` with Redis as the Celery broker/result backend
and a separate worker process:

```bash
make worker
# or
celery -A src.celery_app.celery_app worker --loglevel=INFO --concurrency=1
```

When `JOB_EXECUTION_BACKEND=celery`, PostgreSQL async connection pooling is
disabled for runtime sessions to avoid reusing asyncpg connections across
Celery task event loops.

## Anti-Bot Controls

All active browser scrapers inherit the shared `BaseScraper` anti-bot baseline:
realistic Chromium context profile, per-site storage state, optional
`BROWSER_USER_AGENTS` JSON rotation, `Accept-Language` headers, action jitter,
proxy context assignment, and explicit `blocked` status for `403` / `429` or
visible challenge pages.

Key env vars:

```bash
BROWSER_USER_AGENTS=[]              # empty = derive a Chromium-compatible UA
ANTI_BOT_RETRY_ATTEMPTS=2
ANTI_BOT_BACKOFF_MIN_SECONDS=5.0
ANTI_BOT_BACKOFF_MAX_SECONDS=15.0
PROXY_ROTATION_ENABLED=false
PROXY_URLS=[]
```

The demo runner uses slower pacing than production defaults for visibility.

## Development Commands

```bash
make dev          # Start postgres/redis and API
make worker       # Start a local Celery worker for queued jobs
make test         # Run test suite
make test-cov     # Run tests with coverage
make lint         # Ruff + mypy
make format       # Ruff format/fix
make migrate      # Run Alembic migrations
make docker-up    # Start docker compose services
make docker-logs  # Tail scraper API logs
make demo         # Discovery demo: run all active scrapers
make db-inspect   # DB row counts + recent jobs/part_results
```

Production curl smoke:

```bash
API_BASE_URL=https://<scraper-api-fqdn> \
API_KEY=<api-key> \
N8N_BASE_URL=https://<n8n-fqdn> \
UV_CACHE_DIR=/tmp/uv-cache \
uv run --extra dev python scripts/production_scraper_curl_smoke.py \
  --manifest docs/validation/production_scraper_curl_cases.example.json \
  --output docs/validation/latest_production_curl_smoke.json
```

Headed one-scraper validation:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py \
  --site ml --sku 06K907811B --brand VW --timeout-seconds 120
```

**Database sanity check** (counts `scrape_jobs`, `scrape_items`, `part_results`):

```bash
make db-inspect
```

Targeted checks:

```bash
uv run pytest tests/test_scrapers -v
uv run pytest tests/test_api tests/test_services/test_orchestrator.py -v
uv run ruff check src tests scripts
uv run mypy src
```

## Adding Or Improving A Scraper

1. Read `src/scrapers/base.py`.
2. Add or update `src/scrapers/<site>.py`.
3. Return complete `PartResult` objects.
4. Preserve exact SKU matching and source-specific business rules.
5. Register the scraper in `src/scrapers/__init__.py`.
6. Add focused tests in `tests/test_scrapers/`.

Agent guidance lives in `.agent/`. For a new chat, start from `.agent/prompts/agent-startup.md`.
