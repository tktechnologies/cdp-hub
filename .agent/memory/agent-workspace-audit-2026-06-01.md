# Agent Workspace Audit - 2026-06-01

Scope: root `.agent`, `n8n/`, `scrapers/.agent`, `muvstok-api/.agent`,
root/service `AGENTS.md`, and canonical docs that route agent work.

## Findings

- Root `.agent` had rules, commands, prompts, skills, and sub-agents, but no
  dedicated cross-service knowledge layer for "n8n + API + scraper" ownership.
- n8n had a README but no local `AGENTS.md`, so folder-local agents did not get
  a clear platform-tier redirect.
- Scraper `.agent` had useful skills and commands but no `commands/README.md`
  and no service-level sub-agent briefs. API Diversos already had the most
  complete service workspace.
- A duplicate quality-gate command doc and the old IDE rule tree had already
  been removed in favor of `.agent/rules/`.

## Fixes Applied

- Added `.agent/knowledge/` with:
  - `service-catalog.md` for n8n, Scraper, and API Diversos ownership.
  - `workspace-sync.md` for root/service `.agent` update rules.
- Added `n8n/AGENTS.md` as a local platform-tier redirect.
- Added `scrapers/.agent/commands/README.md`.
- Added scraper service sub-agent briefs for site scraping, API/cache,
  n8n receiver work, and QA.
- Updated root and service indexes to point at the new knowledge and delegation
  structure.

## Current Architecture

```text
root .agent/ = cross-service control plane
  knowledge/ = ownership and sync maps
  rules/ = short task-scoped rules
  skills/ = platform workflows, especially n8n sync
  sub-agents/ = cross-service delegation briefs

n8n/ = platform-owned service surface
  AGENTS.md redirects to root .agent

scrapers/.agent/ = scraper service depth
  skills/commands/sub-agents/memory owned by scraper

muvstok-api/.agent/ = API Diversos service depth
  specs/skills/commands/sub-agents/memory owned by API Diversos
```

## Remaining Watch Items

- ~~`cdp_progress` live workflow ID~~ — resolved 2026-06-05 (`V9I6o32XDoPIRarz`; see `implementation-state.md`).
- Some scripts still read an external user-home MCP config file for credentials.
  That is runtime credential lookup, not project-owned agent documentation.
- Pre-existing application/workflow changes remain dirty and were not reverted
  by this documentation audit.
