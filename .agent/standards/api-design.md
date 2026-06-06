# API Design (Platform)

Cross-service HTTP conventions. Service-specific routes live in each repo.

## Principles

- **Callbacks only** between workers and n8n — no direct worker-to-worker calls.
- **Stable webhook paths:** `scraper-result`, `muvstok-result` (rename only with coordinated deploy).
- **Auth:** `X-API-Key` on protected endpoints in both services.
- **Async jobs:** `POST` returns 202/accepted shape; poll `GET /jobs/{id}` for progress.
- **Idempotency:** StokAPI supports `idempotency_key` on job creation; scraper uses `batch_group_id` for dual-run correlation.

## Scraper (`scrapers/`)

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/api/v1/jobs` | Body: `items[]`, `sites[]`, `callback_url`, `force_refresh` (router sends `false`) |
| `GET` | `/api/v1/jobs/{id}` | Status + `ScrapeJobResult` fields while running |
| `POST` | `/api/v1/dispatch-runs` | Dual-pipeline registry (router) |
| `GET` | `/api/v1/dispatch-runs/active/for-chat/{chat_id}` | Status command lookup |

Schema: [contracts/scraper-job.schema.json](../../contracts/scraper-job.schema.json), [contracts/scraper-callback.schema.json](../../contracts/scraper-callback.schema.json).

## API Diversos / StokAPI (`muvstok-api/`)

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/api/v1/muvstok/jobs` | Body: `skus[]` (strings), `callback_url`, optional `metadata`, `idempotency_key` |
| `GET` | `/api/v1/muvstok/jobs/{id}` | Live counters while `processing` |

Schema: [contracts/stokapi-job.schema.json](../../contracts/stokapi-job.schema.json), [contracts/stokapi-callback.schema.json](../../contracts/stokapi-callback.schema.json).

## Callback URLs

- Must be public HTTPS (validated in StokAPI; scraper trusts configured URLs).
- Router passes notification context via **query parameters** on `callback_url` (not arbitrary `job_metadata` in scraper POST body).
- Header: `X-Webhook-Secret` (values from Key Vault / env — never commit).

## Contract changes

1. Update Pydantic models in the owning service.
2. Update JSON Schema in [contracts/](../../contracts/).
3. Update receiver workflow (`cdp_scraper` or `cdp_stokapi`) and run inject + sync with user approval.
