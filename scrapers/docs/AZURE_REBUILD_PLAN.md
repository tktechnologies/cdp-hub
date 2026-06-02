# Azure Rebuild Plan

**Created:** 2026-05-13
**Last Production Audit:** 2026-05-14

This plan is for rebuilding the scraper production stack from zero after the
current Azure services are deleted by the operator.

## Target Geography

- Resource group: `automation`
- PostgreSQL Flexible Server: **Brazil South**
- All other services: **East US 2**
- Container Registry: East US 2
- Redis for Celery: East US 2
- Key Vault: East US 2
- Container Apps environment: East US 2
- Scrapers API Container App: East US 2
- Celery worker Container App: East US 2
- N8N Container App: East US 2

## Target Services

Required:

- PostgreSQL Flexible Server for durable scraper jobs/results.
- Redis Cache for Celery broker/result backend.
- Azure Container Registry for scraper API/worker and N8N images.
- Azure Key Vault for every secret.
- Azure Container Apps environment.
- Scrapers API Container App.
- Scrapers Celery worker Container App.
- N8N Container App.
- Log Analytics workspace.

Optional but strongly recommended:

- Brazilian ISP/static residential proxy egress first; a two- or three-node
  Azure proxy pool can be added later if measured block rates justify it.
- Azure Monitor alerts for failed jobs, blocked scraper rate, and worker crashes.

## Secret Rules

Store all keys and credentials in Key Vault first, then expose them to Container
Apps through Container App secrets or Key Vault references.

Required secrets:

- `api-key`
- `callback-webhook-secret`
- `database-url`
- `database-url-sync`
- `redis-url`
- `celery-broker-url`
- `celery-result-backend`
- `melibox-user`
- `melibox-pass`
- `proxy-urls`
- N8N encryption key / auth / database secrets as needed.

Never put database passwords, API keys, Redis keys, proxy credentials, Melibox
credentials, or N8N secrets directly in plain Container App env vars.

## Scrapers API Environment

Recommended env:

```text
DATABASE_URL=secretref:database-url
DATABASE_URL_SYNC=secretref:database-url-sync
REDIS_URL=secretref:redis-url
CELERY_BROKER_URL=secretref:celery-broker-url
CELERY_RESULT_BACKEND=secretref:celery-result-backend
JOB_EXECUTION_BACKEND=celery
API_KEY=secretref:api-key
CALLBACK_WEBHOOK_SECRET=secretref:callback-webhook-secret
PLAYWRIGHT_HEADLESS=true
MOCK_SCRAPERS=false
LOG_LEVEL=INFO
LOG_FORMAT=json
SCRAPE_SITES_SEQUENTIAL=true
MAX_CONCURRENT_SCRAPERS=1
SCRAPE_DELAY_MIN=4.0
SCRAPE_DELAY_MAX=10.0
SCRAPER_ACTION_DELAY_MIN_MS=600
SCRAPER_ACTION_DELAY_MAX_MS=1800
MELIBOX_SKU_DELAY_MIN=3
MELIBOX_SKU_DELAY_MAX=8
CREDENTIAL_MELIBOX_USER=secretref:melibox-user
CREDENTIAL_MELIBOX_PASS=secretref:melibox-pass
CREDENTIAL_MELIBOX_URL=https://app.melibox.com.br/advProductPosition
PROXY_ROTATION_ENABLED=true
PROXY_URLS=secretref:proxy-urls
PROXY_FAIL_CLOSED=true
PROXY_AFFINITY_ENABLED=true
PROXY_STATE_PER_IDENTITY=true
```

## Celery Worker Environment

Use the same image as the API, with command:

```text
celery -A src.celery_app.celery_app worker --loglevel=INFO --concurrency=1
```

Recommended worker settings:

```text
JOB_EXECUTION_BACKEND=celery
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_TASK_TIME_LIMIT_SECONDS=3600
PLAYWRIGHT_HEADLESS=true
MOCK_SCRAPERS=false
MAX_CONCURRENT_SCRAPERS=1
```

Keep worker concurrency conservative because each job can launch Playwright
browser contexts.

## Deployment Order

1. Confirm old services are deleted.
2. Provision PostgreSQL in Brazil South.
3. Provision Redis, Key Vault, ACR, Log Analytics, and Container Apps
   environment in East US 2.
4. Save all secrets in Key Vault.
5. Build and push the scraper image to ACR.
6. Run `alembic upgrade head` against the production database.
7. Deploy Scrapers API Container App.
8. Deploy Scrapers Celery worker Container App.
9. Deploy N8N Container App.
10. Run health checks.
11. Run production scraper curl smoke tests:

```bash
API_BASE_URL=https://<scrapers-api-fqdn> \
API_KEY=<api-key> \
N8N_BASE_URL=https://<n8n-fqdn> \
python scripts/production_scraper_curl_smoke.py \
  --manifest docs/validation/production_scraper_curl_cases.example.json \
  --output docs/validation/latest_production_curl_smoke.json
```

## Anti-Bot Best Practices

- Keep `MAX_CONCURRENT_SCRAPERS` low in production until real block rates are known.
- Use jittered action delays, not only fixed waits.
- Keep Melibox pacing at 8-20 seconds per SKU unless field data proves it can be lower.
- Enable the Brazilian ISP/static proxy with site affinity before restoring
  blocked archived sources.
- Do not rotate browser context between Melibox SKUs by default; enable
  `MELIBOX_ROTATE_CONTEXT_PER_SKU=true` only after source-specific validation.
- Return `blocked` honestly when access controls appear; do not mask blocks as
  `not_found`.
- Add observability for status by site: success, no_price, not_found, blocked,
  error, timeout.
- Prefer one SKU/site smoke call at a time for production validation.

## Current Repo Gaps To Fix Before Full Automation

Resolved on 2026-05-14:

- Production API, worker, and N8N Container Apps were verified running and
  healthy in resource group `automation`.
- Deployed `cdpscraperprodacr.azurecr.io/cdp-scraper:melibox-blocked-20260514-0135` to
  both `cdp-scrapers-api-prod` and `cdp-scrapers-worker-prod`.
- Fixed Celery worker database execution by disabling async SQLAlchemy pooling
  under `JOB_EXECUTION_BACKEND=celery`; this resolved the production
  `asyncpg.exceptions.InterfaceError: cannot perform operation: another
  operation is in progress` failure.
- Normalized Azure async PostgreSQL SSL URL handling so `database-url` can be
  used by runtime and audit tooling without driver-specific SSL query errors.
- Verified `/api/v1/lookup` with curl for VW `5U6867287Y20` through the public
  Container App and confirmed the completed job and part row in Azure
  PostgreSQL.
- Ran the full active-scraper production curl manifest. Passing: API health,
  N8N health, GM, VW, EU Imports, and Peça Direta. Failing: Mercado Livre
  `not_found` for the old smoke SKU; Melibox `blocked` with
  `Melibox login entry returned 403/access block`.

Resolved on 2026-05-13:

- Bicep now targets PostgreSQL in Brazil South and the rest of the stack in East
  US 2 with clean production resource names.
- Bicep now deploys separate scraper API, scraper Celery worker, and N8N
  Container Apps.
- `scripts/deploy-azure.sh` now performs a two-phase rebuild, pushes the scraper
  image, runs `alembic upgrade head`, and then rolls out API, worker, and N8N.
- GitHub CD now builds/pushes the scraper image, runs migrations, and updates
  both the API and worker Container Apps.

Still open:

- Add a dedicated infrastructure GitHub workflow for Bicep validation/deployment.
- Repair or replace the Mercado Livre production smoke SKU.
- Resolve Melibox production login-entry `403` access block with an allowed
  outbound IP/proxy or account/IP access policy.
- Configure production proxy URLs with `PROXY_FAIL_CLOSED=true`, or disable
  proxy rotation until the proxy is available.
- Replace Celery Redis `ssl_cert_reqs=CERT_NONE` with certificate validation.
- Add stuck-job/retry/dead-letter cleanup for older pending jobs created before
  the 2026-05-14 worker fix.
