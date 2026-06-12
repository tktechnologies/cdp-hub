# Deploy Scraper

## Prerequisites

- Azure CLI logged in, access to RG `automation`
- Alembic migrations applied: `make -C scrapers migrate`

## CI/CD (preferred)

Monorepo workflow `.github/workflows/cd-prod.yml` (manual dispatch) or push-triggered `.github/workflows/cd-dev.yml` for development.
STOKAI production image deploys use `.github/workflows/cd-stokai-prod.yml`.

Image-only production roll: `make deploy-scraper-prod` → `scripts/deploy-scraper-image.sh`.

## Manual (full stack rebuild)

```bash
./scripts/deploy-scraper-azure.sh
```

Development stack:

```bash
./scripts/deploy-scraper-azure-dev.sh
```

STOKAI production stack (new RG, no n8n):

```bash
./scripts/deploy-stokai-azure.sh
```

Live STOKAI Scraper API:

```text
https://cdp-stokai-scrapers-api-prod.bluewater-4bfb07b7.eastus2.azurecontainerapps.io
```

See [deploy-stokai.md](deploy-stokai.md) before any STOKAI cutover work; the
first validation smoke proved health/auth/cache, but direct price-positive
SKU evidence is still required before routing shared n8n traffic there.

Bicep templates: `infra/scraper-stack.bicep` (direct) or `infra/main.bicep` (platform wrapper).

## Verify

- `GET /api/v1/health` on production API base
- Submit a small test job with `force_refresh: false`
