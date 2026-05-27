# CDP maintenance starter prompts

Copy the **Prompt** block from the file that matches your task into a new Cursor chat. Each prompt bootstraps the right tier, read order, boundaries, and gates.

| Maintenance type | Prompt file |
|------------------|-------------|
| **Scraper** (Playwright, Celery, cache, scrape API) | [scraper.md](scraper.md) |
| **StokAPI / API Diversos** (jobs, worker, Muvstok) | [stokapi.md](stokapi.md) |
| **n8n** (router, receivers, sync — no publish without approval) | [n8n.md](n8n.md) |
| **Infrastructure** (Azure, Bicep, deploy, Key Vault) | [infrastructure.md](infrastructure.md) |
| **Agent workspace** (`.agent/`, Cursor rules, docs alignment) | [agent-workspace.md](agent-workspace.md) |
| **Platform / full stack** (router + both APIs + contracts) | [platform-fullstack.md](platform-fullstack.md) |

**Also useful**

| Purpose | File |
|---------|------|
| Any monorepo / router session | [../platform-startup.md](../platform-startup.md) |
| Scraper n8n + cache E2E validation | [../../../scrapers/.agent/prompts/n8n-cache-integration-test.md](../../../scrapers/.agent/prompts/n8n-cache-integration-test.md) |

Human runbook index: [docs/MAINTENANCE.md](../../../docs/MAINTENANCE.md).
