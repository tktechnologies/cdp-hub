# Deploy Scraper

## Prerequisites

- Azure CLI logged in, access to RG `automation`
- Alembic migrations applied: `make -C scrapers migrate`

## CI/CD (preferred)

Monorepo workflow `.github/workflows/cd-prod.yml` (manual dispatch) or push-triggered `.github/workflows/cd-dev.yml` for development.

Image-only production roll: `make deploy-scraper-prod` → `scripts/deploy-scraper-image.sh`.

## Manual (full stack rebuild)

```bash
./scripts/deploy-scraper-azure.sh
```

Development stack:

```bash
./scripts/deploy-scraper-azure-dev.sh
```

Bicep templates: `infra/scraper-stack.bicep` (direct) or `infra/main.bicep` (platform wrapper).

## Verify

- `GET /api/v1/health` on production API base
- Submit a small test job with `force_refresh: false`
