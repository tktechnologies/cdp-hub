# ADR-0006: Development and production environments

**Status:** Accepted (2026-06-02), amended for shared n8n (2026-06-05)

## Context

CDP runs in Azure (`automation` RG) with production Container Apps and one
shared n8n instance: `cdp-n8n-prod` at
`https://automacao.tktechnologies.com.br`. We need an isolated
**development** stack for safe testing without touching production Telegram,
sheets, or customer traffic.

## Decision

| Layer | Production | Development |
|-------|------------|-------------|
| Resource naming | `*-prod`, `cdp-muv-*` (legacy) | `*-dev` suffix |
| Key Vault | `cdp-scrapers-kv-prod` | `cdp-scrapers-kv-dev` |
| Postgres | `cdp-scrapers-pg-prod` / `cdp_scraper` | `cdp-scrapers-pg-dev` / `cdp_scraper_dev` |
| Redis | `cdp-scrapers-redis-prod` | `cdp-scrapers-redis-dev` |
| Scraper API/worker | `cdp-scrapers-api-prod`, `cdp-scrapers-worker-prod` | `cdp-scrapers-api-dev`, `cdp-scrapers-worker-dev` |
| StokAPI | `cdp-muv-api`, `cdp-muv-worker` | `cdp-muv-api-dev`, `cdp-muv-worker-dev` (provision when ready) |
| n8n | `cdp-n8n-prod` → `automacao.tktechnologies.com.br` | DEV workflow copies in the same n8n instance; `cdp-n8n-dev` is unused for CDP |
| ACR | Shared `cdpscraperprodacr` | Same registry; **dated tags** (`YYYYMMDD-HHMM`, `dev-*`) |
| GitHub | `main` = deployable source | PRs → CI; prod deploy manual approval |
| n8n workflows | Live IDs in `docs/n8n/LIVE_WORKFLOWS.md` | Generated `DEV - ...` copies using DEV env vars, DEV bot credential, DEV sheets, and unique DEV callback paths |

## Deploy scripts

| Environment | Scraper | StokAPI | Image-only scraper |
|-------------|---------|---------|-------------------|
| Production | `scrapers/scripts/deploy-azure.sh` | `deploy_muv_api.sh` / `deploy_muv_worker.sh` | `scripts/deploy-scraper-image.sh` |
| Development | `scrapers/scripts/deploy-azure-dev.sh` or `IMAGE_TAG=dev-* scripts/deploy-scraper-image.sh` with dev app names | `muvstok-api/scripts/deploy_muv_dev.sh` creates/updates `cdp-muv-api-dev` and `cdp-muv-worker-dev` | `IMAGE_TAG=dev-* scripts/deploy-scraper-image.sh` with dev app names |

## n8n

- Production workflow IDs remain canonical in `docs/n8n/LIVE_WORKFLOWS.md`.
- Development workflow IDs are recorded in `.agent/memory/implementation-state.md`.
- Generate DEV JSON with `make n8n-dev-workflows`; first import with
  `make import-n8n-dev`; update later with `make sync-n8n-dev`.
- DEV receiver paths are `POST /webhook/dev-scraper-result` and
  `POST /webhook/dev-muvstok-result`.
- Shared n8n DEV env is configured with
  `scripts/configure-shared-n8n-dev-env.sh`.
- Keep `cdp-n8n-dev` unused for CDP; decommission only with explicit approval.

## Operating guide

Day-to-day DEV vs PROD workflow: [docs/ENVIRONMENTS.md](../ENVIRONMENTS.md).

## Consequences

- Two secret stores; never copy prod API keys into dev bots.
- Google Sheets: use dev copies or tabs for dev runs.
- GitHub deploys DEV from the `dev` branch with immutable `dev-*` tags.
- Production deploy remains `workflow_dispatch` only and should use the
  protected `production` environment for manual approval.
