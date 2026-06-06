# Agent Workspace Sync Contract

Use this contract when a change affects root `.agent`, service `.agent`, or
human docs.

## Ownership

| Workspace | Owns | Must link to |
|-----------|------|--------------|
| `.agent/` | Cross-service routing, n8n platform rules, shared contracts, commands, platform skills, sub-agent briefs | Service `AGENTS.md` and service `.agent/index.md` |
| `scrapers/.agent/` | Scraper rules, scraper skills, scraper commands, service memory, scraper receiver guidance | Root `.agent/boundaries/n8n.md` and `.agent/skills/n8n-router-sync/SKILL.md` |
| `muvstok-api/.agent/` | API Diversos rules, specs alignment, API/worker skills, service commands, service sub-agents | Root `.agent/boundaries/n8n.md` and `.agent/skills/n8n-router-sync/SKILL.md` |
| `n8n/AGENTS.md` | Local redirect for n8n work | Root `.agent` platform docs |

## Update Triggers

| Change | Update |
|--------|--------|
| Router dispatch, `.analisar`, `.sku`, or status behavior | `.agent/skills/`, `.agent/boundaries/n8n.md`, `docs/n8n/LIVE_WORKFLOWS.md` if live facts changed |
| Job or callback JSON shape | Owning service schemas, `contracts/`, receiver workflow docs, root `.agent/standards/api-design.md` if convention changed |
| Google Sheets reporting semantics or formulas | `.agent/rules/google-sheets.md`, `.agent/knowledge/google-sheets-reporting.md`, owning receiver docs/scripts |
| Scraper runtime behavior | `scrapers/.agent/memory/implementation-state.md`, scraper docs, root service catalog only if platform contract changed |
| API Diversos runtime behavior | `muvstok-api/.agent/memory/implementation-state.md`, specs, root service catalog only if platform contract changed |
| New repeatable workflow | Owning `.agent/skills/` or `.agent/commands/`, plus the owning index |
| New delegation role | Owning `sub-agents/README.md` and one scoped brief |

## Rules

- Link from root to service detail instead of copying long service docs.
- Keep live production facts in `memory/implementation-state.md`, not in skills.
- Keep skills procedural and reusable; keep memory factual and dated.
- Keep prompts short enough to bootstrap a fresh chat, then point to skills.
- Keep main [README.md](../../README.md) and [docs/README.md](../../docs/README.md)
  aligned when the architecture, workflows, or setup story changes.
- Do not run `make sync-n8n` or cloud deploy commands without explicit user approval.
