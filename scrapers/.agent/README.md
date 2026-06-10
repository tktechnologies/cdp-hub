# Scraper agent workspace

Canonical routing for AI work on **scrapers/**.

## Layout

| Path | Purpose |
|------|---------|
| `index.md` | Task router |
| `rules.md` | Non-negotiable scraper rules |
| `memory/implementation-state.md` | Scraper runtime only (sites, proxy, cache) — n8n IDs live in root `.agent/memory/` |
| `boundaries/n8n.md` | What this service owns in n8n |
| `prompts/agent-startup.md` | Fresh chat bootstrap |
| `commands/` | Repeatable scraper recipes |
| `sub-agents/` | Scoped delegation briefs |

**Skills** live in `skills/` (this workspace). Do not duplicate skill bodies in platform `.agent/`.

## Platform context

Router dispatch and dual pipeline: [../../docs/architecture/AGENT_ARCHITECTURE.md](../../docs/architecture/AGENT_ARCHITECTURE.md).

Root service catalog: [../../.agent/knowledge/service-catalog.md](../../.agent/knowledge/service-catalog.md).
