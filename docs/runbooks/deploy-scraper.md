# Deploy Scraper

## Prerequisites

- Azure CLI logged in, access to RG `automation`
- Alembic migrations applied: `make -C scrapers migrate`

## CI/CD (preferred)

Push to `main` on scraper repo triggers `.github/workflows/cd.yml` → ACR → Container Apps `cdp-scrapers-api-prod`, `cdp-scrapers-worker-prod`.

## Manual

```bash
cd scrapers
./scripts/deploy-azure.sh
```

## Verify

- `GET /api/v1/health` on production API base
- Submit a small test job with `force_refresh: false`
