# CDP environments — DEV and PRODUCTION

Short operating guide. Architecture detail: [ADR-0006](decisions/ADR-0006-dev-production-environments.md).

## What is what

| | **PRODUCTION** | **DEVELOPMENT** |
|---|----------------|-----------------|
| **Purpose** | Real users (Telegram, email) | Engineers test features safely |
| **Git branch** | `main` (deployable) | `dev` (auto-deploy) |
| **Azure apps** | `*-prod`, `cdp-muv-*` | `*-dev` |
| **Key Vault** | `cdp-scrapers-kv-prod` | `cdp-scrapers-kv-dev` |
| **n8n** | `cdp_router`, `cdp_scraper`, … | `DEV - cdp_*` copies in the **same** instance (`automacao.tktechnologies.com.br`) |
| **Telegram** | Production bot + whitelist | Separate DEV bot (`TELEGRAM_DEV_*`) |
| **Email** | Gmail on prod router + notifier | Disabled on DEV router/notifier initially |
| **Sheets** | Production spreadsheets | Separate DEV sheet IDs (`CDP_DEV_*_SHEET_ID`) |
| **Callbacks** | `/webhook/scraper-result`, `/webhook/muvstok-result` | `/webhook/dev-scraper-result`, `/webhook/dev-muvstok-result` |
| **Deploy** | Manual: GitHub **CD - Production** | Auto on push to `dev`: **CD - Development** |

Never copy production API keys or bot tokens into DEV.

## Who touches what

| Audience | Use |
|----------|-----|
| **Customers** | Production Telegram bot, production email (`EMAIL_ALLOWED_SENDERS` on n8n) |
| **Engineers** | DEV Telegram bot, DEV sheets, DEV Container Apps, `.sku` / `.analisar` against DEV workflows |

## Developer daily workflow

1. Branch from `dev` (or work directly on `dev`).
2. Change code; run local checks (see [promotion checklist](../.agent/workflows/cdp/promote-dev-to-prod.md)).
3. Push to `dev` → **CD - Development** deploys scraper + StokAPI DEV images and runs `make sync-n8n-dev` (when workflow IDs are configured).
4. Validate on DEV: DEV bot → DEV sheets → DEV APIs (URLs from Azure or GitHub `development` env vars).
5. Open PR `dev` → `main`; merge after review.
6. Deploy production: GitHub **Actions → CD - Production → Run workflow** (requires `production` environment approval). Toggle only what changed (scraper, StokAPI API/worker, `sync_n8n`).

Production n8n publish (`make sync-n8n`) always needs explicit human approval — do not run from CI without the workflow checkbox.

## First-time DEV n8n setup (one-time)

Prerequisites: `N8N_API_KEY`, DEV Key Vault secrets, DEV Google Sheets copies.

1. **DEV Telegram bot** — Create via @BotFather; store token in `cdp-scrapers-kv-dev` as `telegram-dev-bot-token`.
2. **n8n credential** — In `automacao.tktechnologies.com.br`, add credential **Telegram DEV account**; note its ID → `N8N_DEV_TELEGRAM_CREDENTIAL_ID`.
3. **Generate + import workflows** (from repo root, with API key and credential ID exported):

   ```bash
   export N8N_API_KEY=...
   export N8N_DEV_TELEGRAM_CREDENTIAL_ID=...
   make import-n8n-dev
   ```

   Prints `CDP_DEV_*_WORKFLOW_ID` for router, scraper, stokapi, progress, and notifier. Record them in [.agent/memory/implementation-state.md](../.agent/memory/implementation-state.md).

4. **GitHub `development` environment** — Set repository variables (and secrets below) from the import output and DEV infra. Required **secrets**: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `N8N_API_KEY`, `N8N_MCP_AUTH_HEADER`, `TELEGRAM_DEV_BOT_TOKEN`. Required **variables**: `N8N_DEV_TELEGRAM_CREDENTIAL_ID`, `CDP_DEV_ROUTER_WORKFLOW_ID`, `CDP_DEV_SCRAPER_WORKFLOW_ID`, `CDP_DEV_STOKAPI_WORKFLOW_ID`, `CDP_DEV_PROGRESS_WORKFLOW_ID`, `CDP_DEV_NOTIFIER_WORKFLOW_ID`, `CDP_DEV_SKUS_SHEET_ID`, `CDP_DEV_RESULTADOS_SHEET_ID`, `CDP_DEV_RESULTADOS_SHEETS_URL`, `TELEGRAM_DEV_ALLOWED_CHAT_IDS`. Optional: `CDP_DEV_MUVSTOK_API_BASE`, `N8N_DEV_TELEGRAM_CREDENTIAL_NAME`, tuning vars in `.env.development.example`.

5. **Shared n8n DEV env** — CD workflow runs `scripts/configure-shared-n8n-dev-env.sh` (sets `CDP_DEV_*` on `cdp-n8n-prod`). Or run locally with Azure CLI + the same env vars.

6. **Ongoing DEV workflow updates** — `make n8n-dev-workflows` then `make sync-n8n-dev` (or rely on CD after IDs exist).

Template for local exports: `.env.development.example`.

## Checklists

### Safe to give customer access (production)

- [ ] Change merged to `main` and reviewed.
- [ ] Promotion checklist completed on `dev` first ([promote-dev-to-prod.md](../.agent/workflows/cdp/promote-dev-to-prod.md)).
- [ ] **CD - Production** run with correct deploy toggles; smoke on prod bot or allowed email.
- [ ] `EMAIL_ALLOWED_SENDERS` includes only intended users (append emails; do not disable whitelist).
- [ ] DEV bot/sheets unchanged; no prod secrets in DEV Key Vault.

### Safe to deploy to production

- [ ] `make -C scrapers test lint` (or CI green).
- [ ] `make check-muvstok`.
- [ ] Contract tests if `contracts/` or callback shapes changed: `cd scrapers && uv run pytest tests/test_contracts/ -v`.
- [ ] DEV validation passed (DEV Telegram run or API smoke).
- [ ] n8n: if workflow changes, user approved `sync_n8n` in prod CD workflow.
- [ ] `docs/n8n/LIVE_WORKFLOWS.md` / `implementation-state.md` updated after prod n8n publish.

## References

- Live prod workflow IDs: [docs/n8n/LIVE_WORKFLOWS.md](n8n/LIVE_WORKFLOWS.md)
- DEV workflow IDs: [.agent/memory/implementation-state.md](../.agent/memory/implementation-state.md)
- Prod deploy workflow: `.github/workflows/cd-prod.yml`
- Dev deploy workflow: `.github/workflows/cd-dev.yml`
