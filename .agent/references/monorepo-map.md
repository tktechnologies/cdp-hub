# CDP Monorepo Map

**Updated:** 2026-06-09

```text
cdp-app/
├── .agent/                 # Platform agent workspace (Tier 1)
│   ├── rules/              # Task-scoped agent rules
│   ├── knowledge/          # Cross-service ownership and sync maps
│   ├── memory/             # Durable project state and decisions
│   ├── references/         # Knowledge maps
│   ├── commands/           # Repeatable command recipes
│   ├── prompts/            # Startup and maintenance prompts
│   ├── skills/             # Reusable platform workflows
│   └── sub-agents/         # Delegation briefs
├── infra/                  # Platform Azure Bicep (canonical)
│   ├── main.bicep          # Platform entry (scraper + optional StokAPI)
│   ├── scraper-stack.bicep # Scraper + n8n resources
│   └── modules/            # ACR, Postgres, Redis, KV, Container Apps, n8n
├── docs/                   # Cross-cutting documentation
├── n8n/
│   ├── src/                # Router/progress Code node source
│   ├── lib/                # Receiver helpers
│   ├── workflows/          # PROD workflow JSON + DEV copies under workflows/dev/
│   ├── sdk/                # Generated workflow SDK files for sync/publish
│   └── settings/
├── contracts/              # JSON Schema shared contracts
├── scripts/
│   ├── sync_workflow_code_from_shared.py
│   ├── sync-all-n8n.sh
│   ├── deploy-scraper-azure.sh
│   └── deploy-scraper-image.sh
├── scrapers/               # Scraper service (Tier 2a)
│   ├── src/
│   ├── tests/
│   ├── alembic/
│   └── .agent/
├── muvstok-api/            # StokAPI (Tier 2b)
│   ├── app/
│   ├── specs/
│   ├── n8n/docs/           # StokAPI receiver guide only (workflows at root n8n/)
│   └── .agent/
├── docker-compose.yml      # Shared postgres + redis
└── Makefile
```

## What belongs where

| Concern | Root | Service subfolder |
|---------|------|-------------------|
| Azure Bicep | `infra/` | — (no `scrapers/infra/`) |
| n8n workflows + router Code | `n8n/` | `muvstok-api/n8n/docs/` (guide only) |
| JSON Schema contracts | `contracts/` | Pydantic models in service `app/` or `src/` |
| CI/CD workflows | `.github/workflows/` | — (no `scrapers/.github/workflows/`) |
| Platform agent docs | `.agent/` | `scrapers/.agent/`, `muvstok-api/.agent/` |
| Deploy scripts (Azure) | `scripts/deploy-scraper-*.sh` | `muvstok-api/scripts/deploy_muv_*.sh` |
| Application code | — | `scrapers/src/`, `muvstok-api/app/` |
| Service tests | — | `scrapers/tests/`, `muvstok-api/tests/` |
| Local Docker deps | `docker-compose.yml`, `docker/` | Service Dockerfiles in each service |

## Key paths

| Task | Path |
|------|------|
| Edit router Code | `n8n/src/*.js` |
| Workflow JSON | `n8n/workflows/` |
| Sync to n8n | `make sync-n8n` |
| Sync DEV workflow copies | `make n8n-dev-workflows`; `make sync-n8n-dev` |
| Scraper API | `scrapers/src/` |
| StokAPI API | `muvstok-api/app/` |
| Platform Bicep | `infra/main.bicep`, `infra/scraper-stack.bicep` |
| Live workflow IDs | `docs/n8n/LIVE_WORKFLOWS.md` |
