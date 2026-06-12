# Deploy STOKAI Production

STOKAI is the new production Azure resource group for Scraper and StokAPI:
`stokai-tk`. The existing `automation` resource group stays intact as rollback
and backup. n8n remains shared on `cdp-n8n-prod` in `automation`.

## Live State

Last validated: 2026-06-12.

| Component | Live value |
|-----------|------------|
| Resource group | `stokai-tk` |
| ACR | `cdpstokaitkacr` |
| Key Vault | `cdp-stokai-kv-prod` |
| Postgres | `cdp-stokai-pg-prod`, DB `cdp_scraper` |
| Redis | `cdp-stokai-redis-prod` |
| Container Apps env | `cdp-stokai-prod-env` |
| Pull identity | `cdp-stokai-prod-pull` |
| Scraper API | `cdp-stokai-scrapers-api-prod` |
| Scraper worker | `cdp-stokai-scrapers-worker-prod` |
| StokAPI API | `cdp-stokai-muv-api` |
| StokAPI worker | `cdp-stokai-muv-worker` |

Public API bases:

```text
https://cdp-stokai-scrapers-api-prod.bluewater-4bfb07b7.eastus2.azurecontainerapps.io
https://cdp-stokai-muv-api.bluewater-4bfb07b7.eastus2.azurecontainerapps.io
```

Current images:

```text
cdpstokaitkacr.azurecr.io/cdp-scraper:20260610-2244
cdpstokaitkacr.azurecr.io/cdp-muv-api:20260612-1406
cdpstokaitkacr.azurecr.io/cdp-muv-worker:20260612-1406
```

Validated status:

- All four active Container App revisions are `Healthy`.
- Scraper health returns `{"status":"ok"}`.
- StokAPI health returns `{"status":"ok","service":"api-diversos","redis":"ok"}`.
- 2026-06-12 Azure audit: all four STOKAI Container Apps were `Running`; the
  Scraper and StokAPI health endpoints returned OK.
- Scraper `/lookup` smoke with SKU `7703062062`, site `gm`, returned
  `not_found`; repeat call hit Redis cache.
- StokAPI jobs for SKU `7703062062` succeeded through API enqueue, Redis
  worker processing, and DB persistence. The callback status was `failed` only
  because the controlled smoke used `https://example.com/...` instead of n8n.
- Direct one-SKU price smoke with SKU `22781768`, brand `GM`, passed on
  2026-06-11 after config fixes:
  - Scraper job `1c362007-e6ca-4f8d-98f1-cd5a547e030b` completed with
    `FOUND_PRICE`, 2 live GM prices, best BRL 1268.78, and callback delivered.
  - StokAPI job `1b8612af-2089-422c-8adf-c30b29c08546` succeeded with
    `FOUND_PRICE`, `callback_status=succeeded`, and one result row.
- No n8n Container App exists in `stokai-tk`.

Keep all project-owned Azure resources in this group named with `cdp-*`, except
ACR `cdpstokaitkacr` because Azure Container Registry names cannot contain
hyphens. Do not modify unrelated resources in `stokai-tk`.

## Full Deploy

```bash
bash scripts/deploy-stokai-azure.sh
```

Script defaults:

- ACR: `cdpstokaitkacr` (ACR names cannot contain hyphens)
- Key Vault: `cdp-stokai-kv-prod`
- Postgres: `cdp-stokai-pg-prod`
- Redis: `cdp-stokai-redis-prod`
- Container Apps env: `cdp-stokai-prod-env`
- Scraper: `cdp-stokai-scrapers-api-prod`, `cdp-stokai-scrapers-worker-prod`
- StokAPI: `cdp-stokai-muv-api`, `cdp-stokai-muv-worker`
- n8n: skipped with `DEPLOY_N8N=false`

Provider credentials are read from the current production Key Vault when
available: Melibox, Muvstok, and `proxy-urls`. API keys, callback secrets, and
database passwords are generated for STOKAI unless explicitly supplied.
When `proxy-urls` is empty or `not-configured`, deploy scripts keep scraper
proxy rotation disabled instead of deploying `PROXY_ROTATION_ENABLED=true` with
no usable proxy endpoints.

The StokAPI worker is a background Redis consumer. It should have no ingress;
the STOKAI wrapper deploys it with `WORKER_INGRESS_ENABLED=false` and one fixed
replica by default.

## Troubleshooting Notes

- `401 Invalid API key` from StokAPI while Scraper auth works usually means
  the StokAPI Container App secret `api-keys` is stale and does not match Key
  Vault secret `api-key`. Refresh the Container App secret from
  `cdp-stokai-kv-prod` and restart the API revision.
- StokAPI worker revision `Degraded` with `0/1 replicas ready` can happen if
  ingress is enabled on the background worker. Disable ingress on
  `cdp-stokai-muv-worker`; the app should run as a Redis consumer with no FQDN.

## Audit Commands

List only CDP-owned Container Apps:

```bash
az containerapp list -g stokai-tk \
  --query "[?starts_with(name, 'cdp-')].{name:name,state:properties.runningStatus,fqdn:properties.configuration.ingress.fqdn,image:properties.template.containers[0].image}" \
  -o table
```

Check active revisions:

```bash
for app in \
  cdp-stokai-scrapers-api-prod \
  cdp-stokai-scrapers-worker-prod \
  cdp-stokai-muv-api \
  cdp-stokai-muv-worker
do
  az containerapp revision list -g stokai-tk -n "$app" \
    --query "[].{name:name,active:properties.active,traffic:properties.trafficWeight,running:properties.runningState,health:properties.healthState,image:properties.template.containers[0].image}" \
    -o table
done
```

Health endpoints:

```bash
curl -fsS https://cdp-stokai-scrapers-api-prod.bluewater-4bfb07b7.eastus2.azurecontainerapps.io/api/v1/health
curl -fsS https://cdp-stokai-muv-api.bluewater-4bfb07b7.eastus2.azurecontainerapps.io/api/v1/muvstok/health
```

Database migration heads:

```sql
SELECT 'scraper' AS stack, version_num FROM alembic_version
UNION ALL
SELECT 'muvstok' AS stack, version_num FROM muvstok_alembic_version
ORDER BY stack, version_num;
```

Expected heads after the 2026-06-11 deploy: scraper `3c9a6b4e0d12`, StokAPI
`20260608_0005`.

## Price Smoke Before n8n Cutover

Before activating STOKAI router/progress in shared n8n, run direct API smokes
with SKUs expected to return at least one price. Do not treat SKU `7703062062`
as a price-positive proof; it only proved request/auth/cache/worker wiring in
the first smoke.

Minimum evidence:

- Scraper `/api/v1/lookup` or `/api/v1/jobs` returns at least one
  `FOUND_PRICE` / valid price from a target source.
- StokAPI `/api/v1/muvstok/jobs` reaches terminal `succeeded` with persisted
  data for the same or related SKU set.
- Database shows the new smoke rows in STOKAI Postgres.
- Callback tests use STOKAI webhook paths only after `CDP_STOKAI_*` is set on
  shared n8n.

## n8n Setup

Configure STOKAI env vars on shared n8n:

```bash
bash scripts/configure-shared-n8n-stokai-env.sh
```

The script discovers `cdp-stokai-scrapers-api-prod` and `cdp-stokai-muv-api` FQDNs from
`stokai-tk` and reads `api-key` / `callback-webhook-secret` from
`cdp-stokai-kv-prod`. Override `CDP_STOKAI_*` values explicitly when testing a
non-default STOKAI deployment.

Generate/import workflow copies:

```bash
make n8n-stokai-workflows
make import-n8n-stokai
```

`import-n8n-stokai` keeps `STOKAI - cdp_router` and
`STOKAI - cdp_progress` inactive. Activate them only during cutover after
deactivating the old `cdp_router` and `cdp_progress`.

Cutover order:

1. Audit STOKAI Azure resources and direct price smokes.
2. Configure `CDP_STOKAI_*` on shared n8n.
3. Import/sync STOKAI receiver and notifier workflows; keep router/progress
   inactive.
4. Smoke callbacks to `/webhook/stokai-scraper-result`,
   `/webhook/stokai-muvstok-result`, and `/webhook/stokai-cdp-notifier`.
5. Confirm no production `automation` run needs to finish.
6. Deactivate old `cdp_router` and `cdp_progress`.
7. Activate `STOKAI - cdp_router` and `STOKAI - cdp_progress`.
8. Run Telegram/email `.sku` smoke through the real production channels.

Rollback: deactivate `STOKAI - cdp_router` and `STOKAI - cdp_progress`, then
reactivate old `cdp_router` and `cdp_progress`. Leave `stokai-tk` intact for
investigation.

## Image-Only Deploy

Use the manual GitHub workflow `CD - STOKAI Production`, or locally:

```bash
RESOURCE_GROUP=stokai-tk \
ACR_NAME=cdpstokaitkacr \
API_APP_NAME=cdp-stokai-scrapers-api-prod \
WORKER_APP_NAME=cdp-stokai-scrapers-worker-prod \
bash scripts/deploy-scraper-image.sh
```

## Verify

- Scraper: `GET /api/v1/health`
- StokAPI: `GET /api/v1/muvstok/health`
- Callback smoke:
  - `/webhook/stokai-scraper-result`
  - `/webhook/stokai-muvstok-result`
  - `/webhook/stokai-cdp-notifier`
