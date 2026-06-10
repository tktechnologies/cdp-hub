# Infrastructure Spec

## Current State
This repository uses Bicep plus Azure CLI deployment automation.

Current deployment assets (monorepo root):
- `infra/scraper-stack.bicep` (orchestrated by `infra/main.bicep`)
- `infra/modules/*.bicep`
- `scripts/deploy-scraper-azure.sh`
- `.github/workflows/cd-prod.yml`
- `Dockerfile`
- `docker-compose.yml` for local development
- Celery worker command: `celery -A src.celery_app.celery_app worker --loglevel=INFO --concurrency=1`

Current Azure resources referenced by scripts/docs for the clean production rebuild:
- Resource group: `automation`
- PostgreSQL location: `brazilsouth`
- ACR, Redis, Key Vault, Log Analytics, Container Apps environment, API, worker, and N8N location: `eastus2`
- Azure Container Registry: `cdpscraperprodacr`
- Azure Container Apps environment: `cdp-scrapers-prod-env`
- Scraper API Container App: `cdp-scrapers-api-prod`
- Scraper worker Container App: `cdp-scrapers-worker-prod`
- N8N Container App: `cdp-n8n-prod`
- PostgreSQL Flexible Server: `cdp-scrapers-pg-prod`
- Redis Cache: `cdp-scrapers-redis-prod`
- Key Vault: `cdp-scrapers-kv-prod`

## Production Audit - 2026-05-14

Live image validated:

```text
cdpscraperprodacr.azurecr.io/cdp-scraper:melibox-blocked-20260514-0135
```

Validated services:
- `cdp-scrapers-api-prod`: running, healthy, public `/api/v1/health` returns
  `200`.
- `cdp-scrapers-worker-prod`: running, healthy, Celery worker command active.
- `cdp-n8n-prod`: running, `/healthz` returns `200`.
- `automacao.tktechnologies.com.br`: bound to `cdp-n8n-prod` with a succeeded
  managed certificate. Public DNS should contain `A 20.41.55.44` and
  `TXT asuid.automacao` equal to the Container Apps environment verification ID.
- `cdp-scrapers-pg-prod`: durable job/result persistence verified from
  `scripts/inspect_scrape_db.py`.

Latest production smoke:
- Passing: API health, N8N health, GM, VW, EU Imports, and Peça Direta.
- Failing source checks: Mercado Livre `06K907811B` returned `not_found`;
  Melibox `51766536` returned `blocked` because the worker receives
  `403 forbidden` at the login entry.

Production queue note:
- Celery worker processes must not reuse pooled asyncpg connections across task
  event loops. Runtime database engine options use `NullPool` when
  `JOB_EXECUTION_BACKEND=celery`.
- Azure async PostgreSQL URLs may keep `?ssl=require` in Key Vault, but runtime
  code normalizes asyncpg SSL flags into `connect_args`.

Scrape result cache (2026-05-21):
- API and worker Container Apps receive `SCRAPE_CACHE_*` env vars from
  `infra/modules/container-app.bicep`.
- `SCRAPE_CACHE_REDIS_URL` uses Azure Redis **database 1** with
  `?ssl_cert_reqs=CERT_NONE` (same TLS pattern as Celery); broker stays on **database 0**.
- API + worker image (callback strip + cache + lookup):
  `cdpscraperprodacr.azurecr.io/cdp-scraper:callback-strip-20260521-1649`.
- Smoke/audit scripts: `scripts/test_scrape_cache_*.sh`,
  `scripts/test_production_5sku_cache_audit.py`,
  `scripts/test_production_5sku_jobs_cache_audit.py`,
  `scripts/production_sku_pool.py` (random 5-SKU pool).
- Callback strip deployed (2026-05-21): `callback-strip-20260521-1649`; worker →
  n8n callbacks validated (E2E execution 369). Optional: trim KV secret (A29).

Open infrastructure risks:
- `tktechnologies.com.br` DNS is currently authoritative at HostGator. Move the
  `automacao` subdomain or the full zone into Azure DNS if custom-domain changes
  need to be managed entirely through Azure CLI/IaC.
- Redis/Celery currently uses `ssl_cert_reqs=CERT_NONE`; replace with
  certificate validation before broader production rollout.
- Proxy rotation is enabled in Container Apps, but `PROXY_URLS` is empty until
  proxy endpoints are provisioned.
- Add a dedicated infrastructure workflow for Bicep validation/deployment.

## IaC Decision
Use **Bicep** for this project.

Why Bicep:
- The project is Azure-only.
- The current workflow already depends on Azure CLI and Azure Container Apps.
- Bicep has first-class support for Azure resources without external providers or state files.
- GitHub Actions can deploy Bicep with `az deployment group create`.
- It keeps the operational model close to what the team already has.

Why not Terraform right now:
- Terraform is excellent for multi-cloud or teams already standardized on Terraform.
- This project does not currently need multi-cloud abstractions.
- Terraform adds remote state management, provider versioning, and a larger operational surface.
- For a small Azure-only scraper stack, that extra machinery is not buying much yet.

Decision:
- Use Bicep as the source of truth for Azure resources.
- Use `scripts/deploy-scraper-azure.sh` for the manual production rebuild flow until a
  dedicated infrastructure GitHub workflow is added.
- Keep app CD focused on building/pushing the scraper image, running migrations,
  and updating the API + worker Container App revisions.

## Target Bicep Modules
Recommended structure:

```text
infra/                          # monorepo root (not under scrapers/)
  main.bicep                    # platform entry
  scraper-stack.bicep           # scraper + n8n stack
  modules/
    acr.bicep
    container-app-env.bicep
    container-app.bicep
    postgres.bicep
    redis.bicep
    key-vault.bicep
    n8n-container-app.bicep
    proxy-pool.bicep
    stokapi-apps.bicep            # placeholder
```

Current repository structure follows this module layout. Validate before deployment with:

```bash
make bicep-validate
# or direct scraper stack:
az bicep build --file infra/scraper-stack.bicep
cp infra/scraper-stack.parameters.example.json infra/scraper-stack.parameters.local.json
az deployment group what-if --resource-group automation --template-file infra/scraper-stack.bicep --parameters @infra/scraper-stack.parameters.local.json
```

The production deployment script performs a two-phase rollout:
1. Deploy shared infrastructure with `deployContainerApps=false`.
2. Build and push the scraper image to ACR.
3. Run `alembic upgrade head` against production PostgreSQL.
4. Deploy the API, worker, and N8N Container Apps with `deployContainerApps=true`.

## Proxy Infrastructure Target
The scraper should start with one validated Brazilian ISP/static residential
egress and stable site/session affinity. Add more proxy endpoints only after
single-proxy block rates, account health, and cache hit rates are measured.

Recommended provider-first shape:
- One authenticated HTTP/HTTPS or SOCKS5 ISP/static residential proxy.
- Proxy credentials stored in Key Vault.
- Container App receives a `PROXY_URLS` secret containing the proxy URL.
- `PROXY_FAIL_CLOSED=true` in production so proxy-enabled revisions do not fall
  back to direct Azure egress.

Azure-managed fallback shape:
- Two or three small Linux proxy VMs, each with its own static Standard Public IP.
- Network Security Group allowing proxy access only from the scraper Container App outbound path or a tightly controlled private network path.
- Squid or Envoy running as an authenticated HTTP CONNECT proxy.
- Proxy credentials stored in Key Vault.
- Container App receives a `PROXY_URLS` secret containing the proxy URLs.

Initial simple form:

```text
PROXY_URLS=[
  "http://user:pass@<br-isp-proxy>:12323"
]
PROXY_ROTATION_ENABLED=true
PROXY_FAIL_CLOSED=true
PROXY_AFFINITY_ENABLED=true
PROXY_STATE_PER_IDENTITY=true
```

## Security Requirements
- Proxy endpoints must not be open to the public internet without authentication.
- Proxy credentials must be stored in Azure Key Vault or Container App secrets.
- Logs must never include proxy passwords.
- Public IPs should be replaceable because anti-bot vendors may burn addresses.
- Each proxy should have health checks and basic metrics.

## GitHub Actions Target
Add a separate infrastructure workflow:

```text
.github/workflows/infra.yml
```

Responsibilities:
- Validate Bicep.
- Deploy to the `automation` resource group.
- Output resource names and proxy endpoint secret references.

The app CD workflow should only build/push images and update the Container App revision.

## Celery Worker Deployment Target

Production should run separate API and worker processes:

- API Container App: serves FastAPI, writes jobs, and enqueues Celery tasks.
- Worker Container App: runs `celery -A src.celery_app.celery_app worker --loglevel=INFO --concurrency=1`.
- Redis: Celery broker and result backend.
- PostgreSQL: durable job/result source of truth.

Required production env vars:

```text
JOB_EXECUTION_BACKEND=celery
CELERY_BROKER_URL=rediss://...
CELERY_RESULT_BACKEND=rediss://...
CELERY_WORKER_CONCURRENCY=1
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_TASK_TIME_LIMIT_SECONDS=3600
```

Keep worker concurrency conservative because each task can launch Playwright browser contexts and consume significant memory.

Required production secrets stored in Key Vault and exposed to Container Apps as
secret refs:

```text
api-key
callback-webhook-secret
database-url
database-url-sync
redis-url
celery-broker-url
celery-result-backend
melibox-user
melibox-pass
proxy-urls
n8n-database-url
n8n-encryption-key
n8n-basic-auth-user
n8n-basic-auth-password
```
