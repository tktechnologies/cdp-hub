# AGENTS.md — CDP Platform (cdp-app)

Instructions for AI agents maintaining the **CDP monorepo** (scrapers + muvstok-api + n8n).

**New chat:** copy-paste bootstrap → [.agent/prompts/new-chat.md](.agent/prompts/new-chat.md)

## Agent tiers

| Tier | Scope | Entry |
|------|--------|--------|
| **1 — Platform** | Router, dual pipeline, `n8n/src/`, contracts | This file → [.agent/index.md](.agent/index.md) |
| **2a — Scraper** | Playwright, Celery, cache, `cdp_scraper` | [scrapers/AGENTS.md](scrapers/AGENTS.md) |
| **2b — StokAPI** | Redis Streams worker, Muvstok, `cdp_stokapi` | [muvstok-api/AGENTS.md](muvstok-api/AGENTS.md) |

Full model: [docs/architecture/AGENT_ARCHITECTURE.md](docs/architecture/AGENT_ARCHITECTURE.md).

## Read order

1. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
2. [docs/n8n/LIVE_WORKFLOWS.md](docs/n8n/LIVE_WORKFLOWS.md)
3. [.agent/index.md](.agent/index.md)
4. [.agent/knowledge/service-catalog.md](.agent/knowledge/service-catalog.md) for cross-service ownership
5. Service `AGENTS.md` when editing one service only

## Core rules

- **Two APIs, one router** — no shared Python between services.
- **Callbacks only** — `scraper-result`, `muvstok-result` webhooks; receivers hand off aggregate final delivery to `cdp_notifier` (`cdp-notifier`).
- **Router Code:** edit `n8n/src/` → `python3 scripts/sync_workflow_code_from_shared.py` → `make sync-n8n` (user approval). Graph/node changes may need MCP `operations` publish — see `docs/n8n/LIVE_WORKFLOWS.md`.
- **No Execute Workflow** for StokAPI production dispatch.
- **Contracts:** [contracts/](contracts/) when changing job or callback JSON.
- **Agent docs:** keep project-owned agent guidance under [.agent/](.agent/) and service `.agent/` workspaces; follow the single-source-of-truth table in [knowledge/workspace-sync.md](.agent/knowledge/workspace-sync.md).
- **Service catalog:** root [.agent/knowledge/](.agent/knowledge/) links n8n, Scraper, and API Diversos ownership.
- **Detalhado seller columns:** use `vendedor`, then canonical `uf`, `empresa`, `cnpj`.
  Do not add/write `estado`; accept `estado` only as a raw input alias that normalizes to `uf`.
- **SKUs robot columns (D–F):** Google Sheets updates match `row_number` from a prior read;
  remap Code must spread the read row and preserve `pairedItem` (see
  [.agent/knowledge/google-sheets-reporting.md](.agent/knowledge/google-sheets-reporting.md)).

## Platform skills

- Router sync: [.agent/skills/n8n-router-sync/SKILL.md](.agent/skills/n8n-router-sync/SKILL.md)
- Dual pipeline: [.agent/skills/dual-pipeline-change/SKILL.md](.agent/skills/dual-pipeline-change/SKILL.md)
- Google Sheets dashboards: [.agent/skills/google-sheets-dashboard/SKILL.md](.agent/skills/google-sheets-dashboard/SKILL.md)

## Maintenance prompts

Copy-paste starters per task type: [.agent/prompts/maintenance/README.md](.agent/prompts/maintenance/README.md) (scraper, StokAPI, n8n, infra, agent workspace, full stack).

## Repo layout

```text
cdp-app/
  .agent/           # Tier 1 — rules, knowledge, commands, prompts, sub-agents, skills
  infra/            # Platform Azure Bicep (scraper stack + StokAPI placeholder)
  n8n/              # Canonical router + workflows
  scrapers/         # Tier 2a
  muvstok-api/      # Tier 2b (gold-standard .agent/)
  docs/             # ARCHITECTURE, SETUP, CONTRIBUTING, ADRs
  contracts/        # JSON Schema
  scripts/          # Platform scripts (n8n sync, deploy, smoke)
```
