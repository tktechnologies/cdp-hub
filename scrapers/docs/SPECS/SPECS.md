# CDP Scraper Specs

## Purpose
This is the source of truth for AI-assisted work in this repository. The repo exists to build and operate the CDP scraper service only.

The service receives automotive part SKU requests, searches supplier sources, normalizes results, persists jobs and results, and exposes an API for CDP and external automation.

Fresh AI-agent chats should start from `.agent/prompts/agent-startup.md`.

Scrape cache operations: `docs/SCRAPE_CACHE_OPERATIONS.md`.

## System Boundaries
In scope:
- FastAPI scraper API.
- Playwright and API-based supplier scrapers.
- Job orchestration.
- PostgreSQL persistence.
- Redis-backed async infrastructure when needed.
- Generic external callback contracts.
- Azure deployment for the scraper service.
- Tests, migrations, operational scripts, and focused docs.

Out of scope:
- Video analysis pipelines.
- Presentation demos.
- Workflow automation project ownership.
- General CDP application features.
- Generic cloud experiments unrelated to the scraper.

## Runtime Components
- `src/main.py`: FastAPI app and lifespan.
- `src/api/routes.py`: authenticated REST API.
- `src/services/orchestrator.py`: job creation, fan-out, aggregation, persistence, callbacks.
- `src/services/scrape_cache.py`: Redis per-site SKU result cache (24h TTL) with PostgreSQL warm fallback.
- `src/celery_app.py` and `src/tasks/scrape_jobs.py`: Celery/Redis worker execution for production jobs.
- `src/scrapers/base.py`: shared Playwright lifecycle, session persistence, normalization, retries, screenshots.
- `src/scrapers/__init__.py`: scraper registry and mock fallback.
- `src/models/schemas.py`: public and internal Pydantic contracts.
- `src/models/database.py`: SQLAlchemy async models and database session setup.
- `src/config.py`: all environment-driven configuration.

## Supported Sites
Current `SiteId` values:
- `gm`
- `ml`
- `vw`
- `eu`
- `pecadireta`
- `melibox`

Archived `SiteId` values (code retained under `src/scrapers/`, not in `SCRAPER_REGISTRY`):
`goparts`, `procurapecas`, `ebay`.
Local demo/discovery scripts may instantiate archived scrapers explicitly for
manual all-source checks, but API defaults and production registry membership
remain limited to active sites.

`MockGMScraper` supports local and CI-like tests when `MOCK_SCRAPERS=true`.

## Data Contracts
Every part result must preserve:
- searched SKU
- found SKU
- exact-match flag
- site ID and human site name
- price and currency
- condition
- availability
- seller name when available
- product URL when available
- origin region
- scrape timestamp
- raw title/source text

Public schema changes must start in `src/models/schemas.py`, then update persistence conversion and tests.

Persisted `scrape_items.site_results` stores the per-site status snapshot for each searched SKU. This preserves `success`, `not_found`, `no_price`, `blocked`, `error`, `timeout`, `error_message`, and search timing when a job is read back from PostgreSQL after Celery execution.

## Business Rules
- Exact SKU matching is required after normalization.
- Normalization strips separators/spaces and uppercases.
- Mercedes parts searched on European import sources remove the first SKU character.
- Mercado Livre returns only new items.
- Prices keep source currency.
- `best_price` is populated only when priced exact-match candidates share one currency.
- Do not choose a cross-currency best price unless currency conversion is explicit and tested.
- Origin should be normalized to useful values such as `Brasil`, `Europa`, `EUA`, or `China`.
- Site status semantics are shared across direct scraper runs and persisted job
  snapshots: `success` means an exact result has a positive price, `not_found`
  means no exact product was found, `no_price` means an exact product was found
  without a positive price, `blocked` means an anti-bot or access restriction
  page was detected and not bypassed, and `error`/`timeout` are reserved for
  unexpected failures or execution timeouts.

## Scraper Rules
- Every production scraper inherits `BaseScraper`.
- Browser credentials and URLs come from `src/config.py`.
- Prefer official APIs over browser automation when they provide the required data.
- Use Playwright for portals, dynamic marketplaces, and authenticated sources.
- `BaseScraper.initialize()` creates a realistic Chromium browser context with
  configurable locale, timezone, viewport, `Accept-Language`, and user-agent
  profile. `BROWSER_USER_AGENTS=[]` derives a Chromium-compatible Linux user
  agent from the installed Playwright browser version; a JSON list enables
  per-context user-agent rotation.
- `BaseScraper.scrape_sku()` records main-document HTTP `403` / `429` responses,
  detects visible CAPTCHA/challenge/access-denied pages, backs off according to
  `ANTI_BOT_RETRY_ATTEMPTS` and `ANTI_BOT_BACKOFF_*`, and returns explicit
  `blocked` status when the site remains restricted.
- Unit tests should mock Playwright or test pure parsing helpers.
- Real browser runs are manual or integration-only.

## Infrastructure Rules
- Production runs on Azure Container Apps.
- PostgreSQL is the source of truth for persisted jobs/results.
- Redis is available for async worker/queue scaling.
- Production job execution uses Celery with Redis as broker/result backend.
- Local development may use `JOB_EXECUTION_BACKEND=local`; production should use `JOB_EXECUTION_BACKEND=celery` plus a separate worker process.
- Workflow automation is owned by a separate project; this repo owns only the scraper API and generic callback contract.
- IaC should be Bicep-first for Azure-only resources. See `docs/SPECS/INFRASTRUCTURE_SPEC.md`.
- Maintenance handoff: `docs/MAINTENANCE_CHECKPOINT.md` (updated 2026-05-21).
- Production images: API `lookup-direct-20260521-1439`, worker
  `scrape-cache-ssl-20260521-1402`. Scrape cache validated on `/lookup` and
  `/jobs` (5-SKU audits via `scripts/production_sku_pool.py`).
- Worker → n8n callbacks fail until `callback_webhook_secret` is stripped on
  load (`src/config.py`) or trimmed in Key Vault.
- Curl smoke: GM, VW, EU, Peça Direta pass; ML smoke SKU stale; Melibox `blocked`
  (403 at login entry). Live n8n drifts from repo (`n8n/docs/AUDIT_2026-05-21.md`).
- Celery worker database engines must avoid pooled asyncpg connections across
  task event loops; use `NullPool` when `JOB_EXECUTION_BACKEND=celery`.
- Azure async PostgreSQL SSL query flags must be normalized into asyncpg
  `connect_args`.

## Proxy Rotation Rules
- Proxy rotation is enabled by `PROXY_ROTATION_ENABLED=true`.
- Proxy endpoints are configured through `PROXY_URLS`.
- The app supports stable site-to-proxy affinity for Playwright browser
  contexts. Round-robin is still available when `PROXY_AFFINITY_ENABLED=false`.
- Proxy rotation is one anti-bot layer; it works with browser profile realism,
  persistent storage state, action jitter, inter-SKU pacing, and blocked-status
  observability.
- Browser state is partitioned by proxy identity when
  `PROXY_STATE_PER_IDENTITY=true`.
- Melibox context rotation is disabled by default; enable
  `MELIBOX_ROTATE_CONTEXT_PER_SKU=true` only after source-specific validation.
- Scrapers should use the shared `BaseScraper.initialize()` lifecycle unless a source-specific override preserves proxy assignment and the configured Playwright headless mode.
- Azure or ISP proxies should start with one stable Brazilian ISP egress and
  low concurrency; add more only after block rates are measured.
- See `docs/SPECS/PROXY_ROTATION_SPEC.md`.

## Documentation Rules
- Any code behavior change must update the relevant docs in the same turn.
- Use `docs/SPECS/DOC_MAINTENANCE_SPEC.md` as the documentation maintenance contract.
- Keep `docs/CHANGELOG.md` and `docs/TASKS.md` current.
- Keep `.agent/` aligned with repeated agent workflows.

## Required Checks
Run the narrowest relevant check first:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests/test_scrapers -v
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests/test_api tests/test_services/test_orchestrator.py -v
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests/test_utils -v
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev ruff check src tests
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev mypy src
```

For visible one-case scraper validation:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py \
  --site ml --sku 06K907811B --brand VW --timeout-seconds 120
```
