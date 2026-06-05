# CDP Documentation Index

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | **Canonical** platform design (services, dual pipeline, n8n, agents) |
| [ENVIRONMENTS.md](ENVIRONMENTS.md) | **DEV vs PRODUCTION** — daily workflow, first-time DEV setup, checklists |
| [ENVIRONMENTS.md](ENVIRONMENTS.md) | DEV vs PRODUCTION — daily workflow, first-time DEV setup, checklists |
| [SETUP.md](SETUP.md) | Local dev quick start |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Change workflow, gates, n8n rules |
| [PLATFORM_OVERVIEW.md](PLATFORM_OVERVIEW.md) | Detailed reference (API tables, Azure, progress) |
| [MAINTENANCE.md](MAINTENANCE.md) | Cross-service maintenance |
| [architecture/AGENT_ARCHITECTURE.md](architecture/AGENT_ARCHITECTURE.md) | Three-tier AI agent model |
| [architecture/DUAL_PIPELINE.md](architecture/DUAL_PIPELINE.md) | `.analisar` / `.sku` behavior |
| [decisions/](decisions/) | Architecture decision records (ADR-0001 … ADR-0006) |
| [decisions/ADR-0006-dev-production-environments.md](decisions/ADR-0006-dev-production-environments.md) | DEV vs production environments (shared n8n, DEV workflow copies) |
| [n8n/LIVE_WORKFLOWS.md](n8n/LIVE_WORKFLOWS.md) | Production workflow IDs |
| [n8n/WORKFLOW_GUIDE.md](n8n/WORKFLOW_GUIDE.md) | Edit, sync, publish workflows |
| [n8n/DATA_CONTRACTS.md](n8n/DATA_CONTRACTS.md) | Scraper result field semantics (Sheets) |
| [runbooks/](runbooks/) | Deploy and n8n release |

**Shared contracts:** [contracts/](../contracts/) (jobs, callbacks, dispatch-runs)

**Service docs:** [scrapers/docs/](../scrapers/docs/), [muvstok-api/specs/](../muvstok-api/specs/)

**Agent workspaces:** [.agent/](../.agent/), [scrapers/.agent/](../scrapers/.agent/), [muvstok-api/.agent/](../muvstok-api/.agent/)

**Service catalog:** [.agent/knowledge/service-catalog.md](../.agent/knowledge/service-catalog.md)

**Task-scoped agent rules:** [.agent/rules/](../.agent/rules/) (platform, scraper, stokapi, n8n, python, contracts, infra)
