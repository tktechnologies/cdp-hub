# Scraper Sub-Agents

Use these only when the user explicitly asks for delegation, sub-agents, or
parallel agent work. Keep writes scoped so delegated agents do not overlap.

| Agent | File | Scope |
|-------|------|-------|
| Site scraper | [site-scraper-agent.md](site-scraper-agent.md) | Playwright/API source scraping and parsing |
| API/cache | [api-cache-agent.md](api-cache-agent.md) | FastAPI jobs, orchestrator, cache, persistence |
| n8n receiver | [n8n-receiver-agent.md](n8n-receiver-agent.md) | `cdp_scraper` callback workflow only |
| QA | [qa-agent.md](qa-agent.md) | Scraper tests, contract checks, regression coverage |
