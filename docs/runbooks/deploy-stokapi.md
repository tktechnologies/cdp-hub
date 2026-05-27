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

## Verify

- `GET /api/v1/muvstok/health` → `service: api-diversos`
- Small job via router or direct `POST /api/v1/muvstok/jobs`
