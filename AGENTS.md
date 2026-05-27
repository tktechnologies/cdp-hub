# AGENTS.md — CDP Platform (cdp-app)

Instructions for AI agents maintaining the **CDP monorepo** (scrapers + muvstok-api + n8n).

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
4. Service `AGENTS.md` when editing one service only

## Core rules

- **Two APIs, one router** — no shared Python between services.
- **Callbacks only** — `scraper-result`, `muvstok-result` webhooks.
- **Router Code:** edit `n8n/src/` → `python3 scripts/sync_workflow_code_from_shared.py` → `make sync-n8n` (user approval).
- **No Execute Workflow** for StokAPI production dispatch.
- **Contracts:** [contracts/](contracts/) when changing job or callback JSON.

## Platform skills

- Router sync: [.agent/skills/n8n-router-sync/SKILL.md](.agent/skills/n8n-router-sync/SKILL.md)
- Dual pipeline: [.agent/skills/dual-pipeline-change/SKILL.md](.agent/skills/dual-pipeline-change/SKILL.md)

## Maintenance prompts

Copy-paste starters per task type: [.agent/prompts/maintenance/README.md](.agent/prompts/maintenance/README.md) (scraper, StokAPI, n8n, infra, agent workspace, full stack).

## Repo layout

```text
cdp-app/
  .agent/           # Tier 1 — commands, standards, sub-agents, skills
  .cursor/rules/    # IDE context (platform, scraper, stokapi, n8n, python, contracts, infra)
  n8n/              # Canonical router + workflows (Phase 1 may retire legacy copies)
  scrapers/         # Tier 2a
  muvstok-api/      # Tier 2b (gold-standard .agent/)
  docs/             # ARCHITECTURE, SETUP, CONTRIBUTING, ADRs
  contracts/        # JSON Schema
```
