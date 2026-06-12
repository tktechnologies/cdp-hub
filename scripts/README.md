# Platform scripts

Scripts at the monorepo root orchestrate **n8n sync**, **deploy**, and **cross-service smoke**. Service-specific ops live under `scrapers/scripts/` and `muvstok-api/scripts/`.

## n8n pipeline (Makefile-wired)

| Script | Purpose |
|--------|---------|
| `sync_workflow_code_from_shared.py` | Inject `n8n/src/*.js` into router/progress JSON |
| `sync-all-n8n.sh` | Full pipeline: inject → patch receivers → SDK → publish |
| `build_cdp_notifier_workflow.py` | Build `n8n/workflows/cdp_notifier.json` |
| `patch_receiver_notifier_handoff.py` | Notifier handoff nodes on receivers |
| `patch_cdp_skus_sheet_nodes.py` | Google Sheets tab alignment |
| `generate_dev_n8n_workflows.py` | Generate `n8n/workflows/dev/dev_*.json` |
| `n8n_publish.py` | Push workflow JSON via REST + MCP |
| `n8n_import_workflow.py` | First-import workflow; prints ID |
| `cdp_skus_sheet_columns.py` | Shared sheet column helpers (imported by patches) |

**Commands:** `make inject-n8n`, `make sync-n8n` (publish requires approval),
`make n8n-dev-workflows`, `make sync-n8n-dev`, `make n8n-stokai-workflows`,
`make import-n8n-stokai`, `make sync-n8n-stokai`

## Deploy and smoke

| Script | Purpose |
|--------|---------|
| `deploy-scraper-image.sh` | Build/push scraper image + roll Container Apps |
| `deploy-scraper-azure.sh` | Full production scraper stack rebuild (Bicep + migrate + apps) |
| `deploy-stokai-azure.sh` | Full STOKAI production stack rebuild in `stokai-tk` (skips n8n) |
| `deploy-scraper-azure-dev.sh` | Development scraper stack (separate KV/Postgres/apps) |
| `configure-shared-n8n-dev-env.sh` | Set `CDP_DEV_*` on shared n8n Container App |
| `configure-shared-n8n-stokai-env.sh` | Set `CDP_STOKAI_*` on shared n8n Container App |
| `smoke_dual_pipeline.sh` | Production dual-pipeline API smoke |

STOKAI direct API smoke should run before n8n cutover. The first 2026-06-11
smoke proved health/auth/cache/worker execution; use a known price-positive SKU
set before activating `STOKAI - cdp_router` and `STOKAI - cdp_progress`.

## Service scripts

| Location | Examples |
|----------|----------|
| `scrapers/scripts/` | `proxy_site_smoke.py`, `patch_scraper_receiver_workflow.py` (deploy wrappers redirect to root) |
| `scrapers/scripts/archive/` | Ad-hoc ops utilities (not in Makefile) |
| `muvstok-api/scripts/` | `deploy_muv_*.sh`, `production_audit.py`, `patch_muvstok_receiver_workflow.py` |
| `muvstok-api/scripts/archive/` | Ad-hoc ops utilities (not in Makefile) |
