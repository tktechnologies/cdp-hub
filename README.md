# CDP Platform

CDP is a monorepo for automotive parts intelligence. It takes SKU requests from
Telegram, Gmail, schedules, or sheets; dispatches public-site scraping and API
Diversos stock lookup in parallel; then delivers structured results to Google
Sheets plus Telegram/email notifications.

AI agents and automation should start with [AGENTS.md](AGENTS.md). Human docs
start at [docs/README.md](docs/README.md).

## What It Does

- **Scraper:** FastAPI + Celery + Playwright searches public supplier and
  marketplace sites with a 24h cache.
- **API Diversos (StokAPI):** FastAPI + Redis Streams worker queries internal
  stock data and persists raw snapshots/results.
- **n8n platform:** `cdp_router` orchestrates `.analisar`, `.sku`, `.status`,
  Gmail, schedules, progress polling, receiver handoff, and final notification.
- **Google Sheets reporting:** `Detalhado`, `Historico`, `Resumo`, and `Painel`
  keep found-price, no-price, not-found, blocked, timeout, and error outcomes
  distinct.

## Runtime Flow

```text
Telegram / Gmail / Schedule
  -> cdp_router (n8n)
      -> Scraper POST /api/v1/jobs
          -> Celery worker -> webhook scraper-result -> cdp_scraper
      -> API Diversos POST /api/v1/muvstok/jobs
          -> Redis Streams worker -> webhook muvstok-result -> cdp_stokapi
  -> receivers write Google Sheets
  -> cdp_notifier sends one aggregate final Telegram/email
```

Production n8n workflows are tracked in
[docs/n8n/LIVE_WORKFLOWS.md](docs/n8n/LIVE_WORKFLOWS.md). DEV workflow copies
run in the shared n8n instance under `DEV - ...` names.

## Repository Layout

| Path | Purpose |
|------|---------|
| [scrapers/](scrapers/) | Scraper API, Celery worker, Playwright scrapers, cache |
| [muvstok-api/](muvstok-api/) | API Diversos/StokAPI API, Redis worker, persistence |
| [n8n/](n8n/) | Router/progress source, workflow JSON, receiver helpers, SDK |
| [contracts/](contracts/) | Shared JSON Schema for jobs, callbacks, dispatch runs |
| [docs/](docs/) | Architecture, runbooks, environment docs, ADRs |
| [.agent/](.agent/) | Platform AI-agent workspace |
| [scrapers/.agent/](scrapers/.agent/) | Scraper service agent workspace |
| [muvstok-api/.agent/](muvstok-api/.agent/) | API Diversos service agent workspace |

## Local Development

```bash
cp .env.example .env
make setup
make migrate-scraper
make dev-scraper   # Scraper API on :8000
make dev-stokapi   # StokAPI/API Diversos on :8001
```

For Docker profiles and full-stack options, see
[.agent/commands/full-stack-dev.md](.agent/commands/full-stack-dev.md) and
[docs/SETUP.md](docs/SETUP.md).

## Quality Gates

```bash
make lint
make test
make check-muvstok
make -C scrapers test lint
```

Run the narrow service checks for the code you touched. Contract changes must
update [contracts/](contracts/) and the owning service tests.

## n8n Sync

Router/progress Code lives in [n8n/src/](n8n/src/). After edits:

```bash
python3 scripts/sync_workflow_code_from_shared.py
make sync-n8n          # publishes live n8n only with explicit approval
```

`make n8n-dev-workflows` regenerates DEV copies under `n8n/workflows/dev/`;
`make sync-n8n-dev` publishes DEV copies when the `CDP_DEV_*_WORKFLOW_ID`
variables are exported.

## Reporting Contract

Found-price success is only `FOUND_PRICE` with `has_valid_price=true`. A row in
`Detalhado` is audit evidence, not success by itself. Seller columns are
`vendedor`, `uf`, `empresa`, `cnpj`; raw `estado` aliases normalize to `uf` and
are not written as output columns.

Details: [.agent/rules/google-sheets.md](.agent/rules/google-sheets.md) and
[docs/n8n/DATA_CONTRACTS.md](docs/n8n/DATA_CONTRACTS.md).

## Key Docs

[Architecture](docs/ARCHITECTURE.md) ·
[Dual pipeline](docs/architecture/DUAL_PIPELINE.md) ·
[Environments](docs/ENVIRONMENTS.md) ·
[n8n live workflows](docs/n8n/LIVE_WORKFLOWS.md) ·
[Contributing](docs/CONTRIBUTING.md)
