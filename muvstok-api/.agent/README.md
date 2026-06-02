# StokAPI agent workspace

**Tier 2b** of the CDP agent architecture. Platform tier: [../../docs/architecture/AGENT_ARCHITECTURE.md](../../docs/architecture/AGENT_ARCHITECTURE.md).

Start with `rules.md`, then `index.md`. For router / dual pipeline / `make sync-n8n`, use platform [../../.agent/index.md](../../.agent/index.md).

## Layout

- `rules.md`: non-negotiable project rules.
- `index.md`: task router for what to read and use.
- `memory/`: durable project context, decisions, implementation state, glossary, and known issues.
- `standards/`: coding, testing, security, observability, and Azure practices.
- `workflows/`: task contracts, implementation flow, reviews, and operations.
- `skills/`: reusable project-specific skills with `SKILL.md` files.
- `commands/`: repeatable command recipes and expected validation signals.
- `sub-agents/`: specialist role briefs for explicit delegation.
- `references/`: compact repo maps and source-oriented notes.
- `prompts/`: startup prompts for fresh AI chat sessions.

When a decision, risk, pattern, or workflow becomes repeatable, update this workspace in the same change.

Root service catalog: [../../.agent/knowledge/service-catalog.md](../../.agent/knowledge/service-catalog.md).
