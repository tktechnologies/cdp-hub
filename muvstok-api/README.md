# API Diversos (StokAPI)

API Diversos SKU ingestion platform: FastAPI, PostgreSQL, Redis Streams workers, Azure Container Apps. Part of the CDP monorepo (`cdp-app`).

**Platform context:** [../docs/PLATFORM_OVERVIEW.md](../docs/PLATFORM_OVERVIEW.md)

## What it does

- Accepts jobs with SKUs and a callback URL (`POST /api/v1/muvstok/jobs`).
- Queues jobs via Redis Streams (`muvstok:jobs`) for background processing.
- Workers fetch SKU data sequentially, persist to PostgreSQL.
- POSTs completion callbacks to n8n (`webhook/muvstok-result`) via **cdp_stokapi**.

## Production architecture (CDP dual pipeline)

Production dispatch is **not** a standalone n8n sender workflow. The monorepo **cdp_router** posts jobs inline:

```text
Telegram / Gmail / Schedule (cdp_router)
  → POST /api/v1/muvstok/jobs  (n8n/src/router_stokapi.js)
  → Redis Stream → cdp-muv-worker
  → PostgreSQL
  → Callback POST …/webhook/muvstok-result
  → cdp_stokapi → Google Sheets + Telegram
```

In parallel, the router dispatches the Scraper API for the same SKU batch. See [../docs/architecture/DUAL_PIPELINE.md](../docs/architecture/DUAL_PIPELINE.md).

## Stack

| Layer | Technology |
|-------|-----------|
| API | Python 3.12, FastAPI, Pydantic v2 |
| Database | PostgreSQL (async SQLAlchemy 2.x, Alembic) |
| Queue | Redis Streams with consumer groups |
| Workers | `app.workers.redis_worker` (sequential SKU processing) |
| Hosting | Azure Container Apps (`cdp-muv-api`, `cdp-muv-worker`) |
| Secrets | Azure Key Vault `cdp-scrapers-kv-prod` |
| n8n receiver | `cdp_stokapi` (`t160mzGPYYlJcrjZ`) |

## Quick start

```bash
docker compose -f docker/docker-compose.yml up --build

uv run ruff check .
uv run mypy .
bash scripts/check_specs.sh
```

## Project structure

```text
app/                    # FastAPI application
├── api/                # Routes and dependencies
├── clients/            # Redis, Muvstok, Key Vault, callback
├── workers/            # Redis Streams consumer
├── services/           # Job, queue, callback orchestration
└── db/                 # Models + Alembic migrations

n8n/
├── workflows/cdp_stokapi.json   # Callback receiver (production)
├── sdk/                         # TypeScript SDK for MCP sync
└── docs/                        # n8n operations guide

specs/                  # 12 planning specs
.agent/                 # AI agent workspace
```

## API endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/v1/muvstok/health` | none | Health check |
| `POST` | `/api/v1/muvstok/jobs` | `X-API-Key` | Submit job (202) |
| `GET` | `/api/v1/muvstok/jobs/{job_id}` | `X-API-Key` | Job status |

Routes and tables use the `muvstok` prefix for compatibility; user-facing branding is **API Diversos**.

## Deployment

| App | Script |
|-----|--------|
| API (`cdp-muv-api`) | `scripts/deploy_muv_api.sh` |
| Worker (`cdp-muv-worker`) | `scripts/deploy_muv_worker.sh` |

n8n sync (all CDP workflows): from monorepo root, `make sync-n8n`.

## AI agents

Start with [AGENTS.md](AGENTS.md) → `.agent/rules.md` → `.agent/index.md`.
