# deploy-stokapi

**Purpose:** Deploy StokAPI (API Diversos) API and worker to Azure.

**Prerequisites**

- Azure CLI; resource group `automation`
- Key Vault secrets current (`cdp-scrapers-kv-prod`)
- Local quality pass: `make check-muvstok` and `make check-specs`

**Deploy (API and worker separately)**

```bash
cd muvstok-api
./scripts/deploy_muv_api.sh
./scripts/deploy_muv_worker.sh
```

Do not combine API and worker into a single deploy script.

**Infrastructure**

StokAPI Container Apps Bicep is a placeholder: [`infra/modules/stokapi-apps.bicep`](../../infra/modules/stokapi-apps.bicep). Full platform template: [`infra/main.bicep`](../../infra/main.bicep) with `deployStokapi=false` until Phase 6 wiring.

**CI**

Monorepo workflow: [`.github/workflows/ci-stokapi.yml`](../../.github/workflows/ci-stokapi.yml) (lint, specs, pytest on PR/push to `muvstok-api/`).

**Verify**

- `GET /api/v1/muvstok/health` → `service: api-diversos`
- Small job via router or `POST /api/v1/muvstok/jobs`

**Runbook:** [docs/runbooks/deploy-stokapi.md](../../docs/runbooks/deploy-stokapi.md)
