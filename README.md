# CDP Platform (cdp-app)

Monorepo for **automotive parts intelligence**: public-site scraping (Scraper) and internal stock (StokAPI / API Diversos), orchestrated by n8n.

**Agents:** read [AGENTS.md](AGENTS.md) first.

## Quick start

```bash
cp .env.example .env
make dev
make -C scrapers setup   # first time: deps + migrate
make -C scrapers dev     # :8000
```

## Layout

| Path | Purpose |
|------|---------|
| [scrapers/](scrapers/) | Scraper API + Celery + Playwright |
| [muvstok-api/](muvstok-api/) | API Diversos + Redis Streams worker |
| [n8n/](n8n/) | Router source, workflow JSON, settings |
| [docs/](docs/) | Platform architecture and runbooks |
| [.agent/](.agent/) | Platform AI agent workspace |
| [contracts/](contracts/) | Shared JSON Schema contracts |

## Dual pipeline

```text
Telegram / Gmail / Schedule
  → cdp_router (n8n)
      ├─ POST Scraper /api/v1/jobs → Celery → webhook scraper-result → cdp_scraper
      └─ POST StokAPI /api/v1/muvstok/jobs → Redis worker → webhook muvstok-result → cdp_stokapi
  → Google Sheets + Telegram
```

Details: [docs/architecture/DUAL_PIPELINE.md](docs/architecture/DUAL_PIPELINE.md)

## Commands

```bash
make sync-n8n          # inject + push workflows (user approval for publish)
make test lint         # all quality gates
make check-muvstok     # StokAPI ruff + mypy
make -C scrapers test  # scraper pytest
```

## Documentation

[Index](docs/README.md) · [Platform overview](docs/PLATFORM_OVERVIEW.md) · [n8n workflows](docs/n8n/LIVE_WORKFLOWS.md)
