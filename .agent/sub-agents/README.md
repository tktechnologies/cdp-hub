# Platform Sub-Agents

Specialist role briefs for **explicit delegation** only (parallel agents or scoped handoffs).

Each brief defines: ownership, read-first paths, expected output, and boundaries.

| Agent | File | Scope |
|-------|------|--------|
| Backend API | [backend-api.md](backend-api.md) | Cross-service API contracts, dispatch-runs, job shapes |
| Scraper specialist | [scraper-specialist.md](scraper-specialist.md) | Delegate to Tier 2a — Playwright, Celery, cache |
| API Diversos specialist | [api-diversos-specialist.md](api-diversos-specialist.md) | Delegate to Tier 2b — jobs, worker, Muvstok, receiver |
| Database | [database.md](database.md) | PostgreSQL schema/migrations in either service |
| Azure infra | [azure-infra.md](azure-infra.md) | Container Apps, Key Vault, ACR, deploy scripts |
| n8n workflow | [n8n-workflow.md](n8n-workflow.md) | Router Code, workflow JSON, sync/publish |
| QA testing | [qa-testing.md](qa-testing.md) | Quality gates, smoke scripts, contract validation |

Gold standard for service sub-agents: `muvstok-api/.agent/sub-agents/`.
