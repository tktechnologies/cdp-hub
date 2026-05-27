# Infrastructure Reference For N8N Agents

> **Deprecated.** Platform infra: [infra/README.md](../../../infra/README.md). Scraper Azure: `scrapers/infra/`, `scrapers/docs/SPECS/INFRASTRUCTURE_SPEC.md`.

Last updated: 2026-05-21

Production handoff: `docs/MAINTENANCE_CHECKPOINT.md`. Callback blocker: Key Vault
`callback-webhook-secret` may include trailing `\r` — deploy `src/config.py` strip
or trim secret before expecting worker → n8n callbacks.

## Runtime Topology

Production runs on Azure:

```text
N8N workflow
  -> Scraper API Container App
    -> Redis/Celery queue
      -> Scraper worker Container App
        -> Playwright scraper browser sessions
        -> PostgreSQL job/result persistence
        -> N8N callback webhook
```

The API should respond quickly to `POST /api/v1/jobs`. The long-running scrape
happens in the worker.

## Azure Resource Inventory

| Resource | Name | Purpose |
|---|---|---|
| Resource group | `automation` | Production resource group. |
| ACR | `cdpscraperprodacr` | Stores scraper container images. |
| Container Apps environment | `cdp-scrapers-prod-env` | Hosts API, worker, and N8N. |
| API Container App | `cdp-scrapers-api-prod` | Public FastAPI API. |
| Worker Container App | `cdp-scrapers-worker-prod` | Private Celery worker. |
| N8N Container App | `cdp-n8n-prod` | Public N8N instance. |
| PostgreSQL | `cdp-scrapers-pg-prod` | Durable scraper and N8N databases. |
| Redis | `cdp-scrapers-redis-prod` | Celery broker/result backend. |
| Key Vault | `cdp-scrapers-kv-prod` | Production secrets. |

Regions:
- PostgreSQL: `brazilsouth`
- ACR, Redis, Key Vault, Log Analytics, Container Apps, API, worker, N8N:
  `eastus2`

N8N public custom URL:

```text
https://automacao.tktechnologies.com.br
```

Latest smoke artifact also references the Container App FQDN:

```text
https://cdp-n8n-prod.bravecoast-b14d791e.eastus2.azurecontainerapps.io
```

## Service Roles

API Container App:
- Serves FastAPI routes under `/api/v1`.
- Validates `X-API-Key`.
- Inserts `scrape_jobs`.
- Queues Celery tasks when `JOB_EXECUTION_BACKEND=celery`.
- Reads durable job status from PostgreSQL.

Worker Container App:
- Runs:

```text
celery -A src.celery_app.celery_app worker --loglevel=INFO --concurrency=1
```

- Pulls queued scrape jobs from Redis.
- Launches Playwright scraper sessions.
- Persists `scrape_items` and `part_results`.
- Sends final callback payload to N8N when `callback_url` is present.

N8N Container App:
- Runs `docker.io/n8nio/n8n:latest`.
- Uses PostgreSQL database `n8n`.
- Uses HTTPS public webhooks through `WEBHOOK_URL`.
- Stores workflow credentials and execution history in the N8N database.

PostgreSQL:
- Database `cdp_scraper`: scraper jobs/results.
- Database `n8n`: N8N persistence.

Redis:
- `rediss://...:6380/0` is used for Celery broker and result backend.

## Important Production Environment Variables

API and worker:

```text
DATABASE_URL
DATABASE_URL_SYNC
REDIS_URL
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
API_KEY
CALLBACK_WEBHOOK_SECRET
CREDENTIAL_MELIBOX_USER
CREDENTIAL_MELIBOX_PASS
PROXY_URLS
PROXY_ROTATION_ENABLED
PLAYWRIGHT_HEADLESS=true
MOCK_SCRAPERS=false
JOB_EXECUTION_BACKEND=celery
MAX_CONCURRENT_SCRAPERS
SCRAPE_DELAY_MIN
SCRAPE_DELAY_MAX
SCRAPER_ACTION_DELAY_MIN_MS
SCRAPER_ACTION_DELAY_MAX_MS
MELIBOX_SKU_DELAY_MIN
MELIBOX_SKU_DELAY_MAX
CREDENTIAL_MELIBOX_URL
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_TASK_TIME_LIMIT_SECONDS=3600
```

N8N (CDP scraper + Muvstok workflows read these from the container env):

```text
CDP_SCRAPER_API_BASE          -> secret cdp-scrapers-api-base
CDP_MUVSTOK_API_BASE          -> secret cdp-muvstok-api-base
CDP_API_KEY                   -> secret api-key (Key Vault: api-key)
CDP_MUVSTOK_API_KEY           -> secret api-key
CDP_CALLBACK_WEBHOOK_SECRET   -> secret callback-webhook-secret
CDP_MUVSTOK_CALLBACK_WEBHOOK_SECRET -> secret callback-webhook-secret
CALLBACK_WEBHOOK_SECRET       -> secret callback-webhook-secret
CDP_N8N_WEBHOOK_PATH=webhook/scraper-result
CDP_MUVSTOK_WEBHOOK_PATH=webhook/muvstok-result
```

Key Vault `cdp-scrapers-kv-prod` (resource group `automation`):

| Secret | Used by |
|---|---|
| `api-key` | Scraper API, Muvstok API, N8N `CDP_*_API_KEY` |
| `callback-webhook-secret` | APIs + N8N webhook verification |
| `cdp-scrapers-api-base` | N8N scraper jobs (IaC; optional until next deploy) |
| `cdp-muvstok-api-base` | N8N Muvstok jobs (IaC; optional until next deploy) |

Container App `cdp-n8n-prod` mirrors Key Vault values as app secrets (`secretRef`).
Bicep: `scrapers/infra/modules/n8n-container-app.bicep` and `key-vault.bicep`.

N8N core:

```text
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER
DB_POSTGRESDB_PASSWORD
DB_POSTGRESDB_SSL_ENABLED=true
N8N_ENCRYPTION_KEY
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER
N8N_BASIC_AUTH_PASSWORD
N8N_PORT=5678
N8N_PROTOCOL=https
N8N_HOST=automacao.tktechnologies.com.br
N8N_EDITOR_BASE_URL=https://automacao.tktechnologies.com.br
WEBHOOK_URL=https://automacao.tktechnologies.com.br/
N8N_DIAGNOSTICS_ENABLED=false
N8N_VERSION_NOTIFICATIONS_ENABLED=false
```

## Queue And Scaling Notes

Production uses Celery to avoid losing long-running scrape jobs when API HTTP
connections close.

Current worker posture is conservative:
- Worker max replicas: 1
- Worker command concurrency: 1
- Worker prefetch multiplier: 1
- Per-job task time limit: 3600 seconds

N8N should batch jobs thoughtfully. Do not send hundreds of SKUs into one
workflow HTTP request and wait for results. Use asynchronous jobs plus callback.

The request schema allows up to 500 `items`, but practical batch size should be
chosen based on sites selected, source health, and operational urgency. Smaller
batches give clearer failure isolation.

## Persistence Model

Main scraper tables:

| Table | Purpose |
|---|---|
| `scrape_jobs` | One row per submitted job. |
| `scrape_items` | One row per SKU within a job. |
| `part_results` | One row per product/listing/offer found. |
| `session_states` | Browser/session health metadata by site. |

N8N agents should use the API as the integration boundary. Direct database
queries are for diagnostics or admin reporting, not normal workflow logic.

## Operational Risks Agents Must Respect

| Risk | Practice |
|---|---|
| Long scrape duration | Use `/jobs` + callback instead of synchronous `/lookup`. |
| Mixed currency results | Do not calculate global cheapest price without conversion. |
| Marketplace noise | Trust `exact_match`; do not promote non-exact listings as quotes. |
| Anti-bot blocks | Treat `blocked` as source health, not part unavailability. |
| Melibox production access | Expect possible `blocked` until proxy/access issue is resolved. |
| Redis TLS validation | Current Celery URL uses `ssl_cert_reqs=CERT_NONE`; track as infra hardening. |
| Proxy rotation | Production warns if enabled with empty `PROXY_URLS`. |

