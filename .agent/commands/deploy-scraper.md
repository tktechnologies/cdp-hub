# deploy-scraper

**Purpose:** Deploy the Scraper service to Azure Container Apps (production).

**Prerequisites**

- Azure CLI logged in; access to resource group `automation`
- Migrations applied: `make migrate-scraper`
- Secrets in Key Vault / parameter file — never commit real values

**Preferred (CI/CD)**

Push to `main` with scraper changes triggers [`.github/workflows/ci-scraper.yml`](../../.github/workflows/ci-scraper.yml) (validate) and the scraper CD workflow under `scrapers/.github/workflows/cd.yml` when that path is configured for the remote.

**Manual deploy**

```bash
cd scrapers
./scripts/deploy-scraper-azure.sh
```

**Infrastructure (what-if only from monorepo root)**

```bash
make bicep-build
make bicep-what-if   # does not apply changes
```

Platform Bicep entry: [`infra/main.bicep`](../../infra/main.bicep) → [`infra/scraper-stack.bicep`](../../infra/scraper-stack.bicep).

**Verify**

- `GET /api/v1/health` on production API base
- Small lookup/job with `force_refresh: false`

**Runbook:** [docs/runbooks/deploy-scraper.md](../../docs/runbooks/deploy-scraper.md)
