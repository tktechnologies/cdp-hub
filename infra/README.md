# CDP Platform Infrastructure (Azure Bicep)

Platform-level IaC for the CDP monorepo. **Does not deploy from CI by default** — use service runbooks and explicit `az deployment` with approved parameters.

## Layout

| Path | Purpose |
|------|---------|
| `main.bicep` | Platform entry — orchestrates scraper stack + optional StokAPI apps |
| `scraper-stack.bicep` | Scraper + n8n Azure resources (ACR, Postgres, Redis, Key Vault, Container Apps) |
| `main.parameters.example.json` | Platform wrapper parameters (no secrets committed) |
| `main.parameters.development.example.json` | Development platform parameters |
| `scraper-stack.parameters.example.json` | Scraper-stack parameters for direct deploy scripts |
| `modules/` | Bicep modules (ACR, Postgres, Redis, Key Vault, Container Apps, n8n, StokAPI placeholder) |

StokAPI Container Apps are deployed via `muvstok-api/scripts/deploy_muv_*.sh` today; `modules/stokapi-apps.bicep` is a Phase 6 placeholder.

STOKAI production lives in resource group `stokai-tk` with CDP-owned resources
named `cdp-*` (`cdp-stokai-kv-prod`, `cdp-stokai-pg-prod`,
`cdp-stokai-redis-prod`, `cdp-stokai-prod-env`, and CDP Container Apps). ACR is
`cdpstokaitkacr` because Azure Container Registry names cannot contain hyphens.
n8n is intentionally not deployed in `stokai-tk`; shared n8n remains in
`automation`.

## Validate locally (no deploy)

```bash
make bicep-build
make bicep-what-if   # requires Azure CLI login + RG access
```

Direct scraper-stack what-if:

```bash
az bicep build --file infra/scraper-stack.bicep
az deployment group what-if \
  --resource-group automation \
  --template-file infra/scraper-stack.bicep \
  --parameters @infra/scraper-stack.parameters.example.json
```

## Deploy runbooks

| Stack | Script |
|-------|--------|
| Scraper production (full rebuild) | `scripts/deploy-scraper-azure.sh` |
| STOKAI production (full rebuild, no n8n) | `scripts/deploy-stokai-azure.sh` |
| Scraper development | `scripts/deploy-scraper-azure-dev.sh` |
| Scraper image only (prod API + worker) | `scripts/deploy-scraper-image.sh` |
| StokAPI API | `muvstok-api/scripts/deploy_muv_api.sh` |
| StokAPI worker | `muvstok-api/scripts/deploy_muv_worker.sh` |

See also [docs/runbooks/deploy-scraper.md](../docs/runbooks/deploy-scraper.md),
[docs/runbooks/deploy-stokai.md](../docs/runbooks/deploy-stokai.md), and
[docs/runbooks/deploy-stokapi.md](../docs/runbooks/deploy-stokapi.md).
