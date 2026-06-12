# Deploy StokAPI (API Diversos)

## Prerequisites

- Azure CLI, RG `automation`
- Key Vault secrets current

## Deploy

```bash
cd muvstok-api
./scripts/deploy_muv_api.sh    # API only
./scripts/deploy_muv_worker.sh # Worker only
```

Deploy API and worker separately — do not use a single script for both.

STOKAI production uses the same scripts with explicit target env:

```bash
RG=stokai-tk ACR=cdpstokaitkacr KV=cdp-stokai-kv-prod \
API_APP=cdp-stokai-muv-api ENV_NAME=cdp-stokai-prod-env MI_NAME=cdp-stokai-prod-pull \
./scripts/deploy_muv_api.sh

RG=stokai-tk ACR=cdpstokaitkacr KV=cdp-stokai-kv-prod \
API_APP=cdp-stokai-muv-api WORKER_APP=cdp-stokai-muv-worker \
ENV_NAME=cdp-stokai-prod-env MI_NAME=cdp-stokai-prod-pull \
WORKER_INGRESS_ENABLED=false \
./scripts/deploy_muv_worker.sh
```

The StokAPI worker is not an HTTP service. For STOKAI, keep
`WORKER_INGRESS_ENABLED=false`; otherwise Azure Container Apps may mark the
revision degraded while the Redis worker itself is functioning.

## Verify

- `GET /api/v1/muvstok/health` → `service: api-diversos`
- Small job via router or direct `POST /api/v1/muvstok/jobs`
