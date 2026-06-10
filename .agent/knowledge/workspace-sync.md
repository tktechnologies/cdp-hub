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

## Single source of truth (do not duplicate)

| Fact | Canonical location | Service workspaces |
|------|-------------------|-------------------|
| Live workflow IDs + active version UUIDs | `.agent/memory/implementation-state.md`, `docs/n8n/LIVE_WORKFLOWS.md` | Link only — never copy ID tables |
| n8n ownership, webhooks, router Code files | `.agent/boundaries/n8n.md` | `boundaries/n8n.md` = service slice + link up |
| Reporting / Sheets semantics (`FOUND_PRICE`, `BLOCKED`, …) | `.agent/rules/google-sheets.md`, `.agent/knowledge/google-sheets-reporting.md` | One-line pointer + service field names only |
| Platform architecture rules | `.agent/rules.md`, `docs/ARCHITECTURE.md` | Service `rules.md` = service-specific only |
| Scraper runtime (sites, proxy, cache) | `scrapers/.agent/memory/implementation-state.md` | — |
| StokAPI runtime (queue, dup-SKU cache, deploy) | `muvstok-api/.agent/memory/implementation-state.md` | — |
| Cross-service deploy snapshot | `.agent/memory/implementation-state.md` | Service memory links up for IDs/tags |

Bootstrap prompts (`new-chat.md`, `platform-startup.md`, maintenance prompts) may name workflows but must **not** embed workflow IDs — agents resolve IDs from the canonical files above.

## Rules

- Edit platform `.agent/memory/implementation-state.md` first for live n8n IDs and deploy facts; `scrapers/docs/MAINTENANCE_CHECKPOINT.md` is the scraper-facing summary.
- Link from root to service detail instead of copying long service docs.
- Keep live production facts in platform `memory/implementation-state.md`, not in skills, service memory, or prompts.
- Keep skills procedural and reusable; keep memory factual and dated.
- Keep prompts short enough to bootstrap a fresh chat, then point to skills.
- Keep main [README.md](../../README.md) and [docs/README.md](../../docs/README.md)
  aligned when the architecture, workflows, or setup story changes.
- Do not run `make sync-n8n` or cloud deploy commands without explicit user approval.
