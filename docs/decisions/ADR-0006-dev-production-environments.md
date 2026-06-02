# ADR-0006: Development and production environments

**Status:** Accepted (2026-06-02)

## Context

CDP runs in Azure (`automation` RG) with production Container Apps and a single live n8n instance. We need an isolated **development** stack for safe testing without touching production Telegram, sheets, or customer traffic.

## Decision

| Layer | Production | Development |
|-------|------------|-------------|
| Resource naming | `*-prod`, `cdp-muv-*` (legacy) | `*-dev` suffix |
| Key Vault | `cdp-scrapers-kv-prod` | `cdp-scrapers-kv-dev` |
| Postgres | `cdp-scrapers-pg-prod` / `cdp_scraper` | `cdp-scrapers-pg-dev` / `cdp_scraper_dev` |
| Redis | `cdp-scrapers-redis-prod` | `cdp-scrapers-redis-dev` |
| Scraper API/worker | `cdp-scrapers-api-prod`, `cdp-scrapers-worker-prod` | `cdp-scrapers-api-dev`, `cdp-scrapers-worker-dev` |
| StokAPI | `cdp-muv-api`, `cdp-muv-worker` | `cdp-muv-api-dev`, `cdp-muv-worker-dev` (provision when ready) |
| n8n | `cdp-n8n-prod` → `automacao.tktechnologies.com.br` | `cdp-n8n-dev` (separate FQDN) or dev workflow copies |
| ACR | Shared `cdpscraperprodacr` | Same registry; **dated tags** (`YYYYMMDD-HHMM`, `dev-*`) |
| GitHub | `main` = deployable source | PRs → CI; prod deploy manual approval |
| n8n workflows | Live IDs in `docs/n8n/LIVE_WORKFLOWS.md` | Same JSON; dev instance uses dev API env vars |

## Deploy scripts

| Environment | Scraper | StokAPI | Image-only scraper |
|-------------|---------|---------|-------------------|
| Production | `scrapers/scripts/deploy-azure.sh` | `deploy_muv_api.sh` / `deploy_muv_worker.sh` | `scripts/deploy-scraper-image.sh` |
| Development | `scrapers/scripts/deploy-azure-dev.sh` | `muvstok-api/scripts/deploy_muv_dev.sh` | `IMAGE_TAG=dev-* scripts/deploy-scraper-image.sh` with dev app names |

## n8n

- Production workflow IDs remain canonical in `docs/n8n/LIVE_WORKFLOWS.md`.
- `cdp_progress`: import once per n8n instance; set `CDP_PROGRESS_WORKFLOW_ID` before `make sync-n8n`.
- Dev: after `cdp-n8n-dev` exists, import workflows and point `CDP_SCRAPER_API_BASE` / `CDP_STOKAPI_API_BASE` at dev FQDNs.

## Consequences

- Two secret stores; never copy prod API keys into dev bots.
- Google Sheets: use dev copies or tabs for dev runs.
- CI runs on GitHub; does not auto-deploy to Azure.
