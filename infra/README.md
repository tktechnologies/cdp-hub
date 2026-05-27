# CDP Platform Infrastructure (Azure Bicep)

Platform-level IaC for the CDP monorepo. **Does not deploy from CI by default** — use service runbooks and explicit `az deployment` with approved parameters.

## Layout

| Path | Purpose |
|------|---------|
| `main.bicep` | Platform entry — orchestrates scraper stack + optional StokAPI apps |
| `main.parameters.example.json` | Example parameters (no secrets committed) |
| `modules/stokapi-apps.bicep` | StokAPI Container Apps placeholder (Phase 6) |
| `../scrapers/infra/modules/` | Canonical scraper modules (ACR, Postgres, Redis, Container Apps, n8n) |

Scraper modules remain under `scrapers/infra/` to avoid duplicating large Bicep files. Root `main.bicep` references them via relative paths.

## Validate locally (no deploy)

```bash
make bicep-build
make bicep-what-if   # requires Azure CLI login + RG access
```

## Service deploy runbooks

- Scraper: [docs/runbooks/deploy-scraper.md](../docs/runbooks/deploy-scraper.md)
- StokAPI: [docs/runbooks/deploy-stokapi.md](../docs/runbooks/deploy-stokapi.md)
