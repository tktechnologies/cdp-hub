# CDP Platform — Agent Workspace

**Tier 1** of the CDP agent architecture. See [docs/architecture/AGENT_ARCHITECTURE.md](../docs/architecture/AGENT_ARCHITECTURE.md).

## Start here

| File | Purpose |
|------|---------|
| [prompts/new-chat.md](prompts/new-chat.md) | **Copy-paste every new Cursor chat** |
| [index.md](index.md) | Task routing (platform vs service) |
| [rules.md](rules.md) | Non-negotiable platform rules |
| [rules/](rules/) | Task-scoped rule summaries for platform, services, n8n, Python, contracts, infra |
| [knowledge/](knowledge/) | Cross-service ownership and workspace sync maps |
| [memory/implementation-state.md](memory/implementation-state.md) | Live workflow IDs, cross-service snapshot |
| [references/monorepo-map.md](references/monorepo-map.md) | Directory map |

## Boundaries

- [boundaries/services.md](boundaries/services.md) — scraper vs stokapi vs platform
- [boundaries/n8n.md](boundaries/n8n.md) — three workflows, webhooks, n8n/src

## Workspace Structure

- [rules/](rules/) — task-scoped agent rules
- [knowledge/](knowledge/) — service catalog and root/service workspace sync contract
- [memory/](memory/) and [references/](references/) — durable project knowledge
- [standards/](standards/) — coding, API design, security, observability
- [sub-agents/](sub-agents/) — delegation briefs (backend, n8n, Azure, QA, …)
- [commands/](commands/) — sync-n8n, quality gates, full-stack dev

## Platform skills

| Skill | When |
|-------|------|
| [skills/n8n-router-sync/SKILL.md](skills/n8n-router-sync/SKILL.md) | Edit router, inject, `make sync-n8n` |
| [skills/dual-pipeline-change/SKILL.md](skills/dual-pipeline-change/SKILL.md) | `.analisar` / `.sku` behavior |

## Service workspaces (Tier 2)

| Service | Entry |
|---------|--------|
| n8n | [n8n/AGENTS.md](../n8n/AGENTS.md) → platform `.agent/` |
| Scraper | [scrapers/AGENTS.md](../scrapers/AGENTS.md) → `scrapers/.agent/` (skills in `.agent/skills/`) |
| StokAPI | [muvstok-api/AGENTS.md](../muvstok-api/AGENTS.md) → `muvstok-api/.agent/` |

## Workflows

| Path | Purpose |
|------|---------|
| [workflows/cdp/](workflows/cdp/) | CDP release checklists (n8n, etc.) |
| [workflows/README.md](workflows/README.md) | AIOX personas (optional; not in repo) |

## Prompts

- [prompts/platform-startup.md](prompts/platform-startup.md) — monorepo / router sessions
