# ADR-0005: Three-tier agent workspaces

**Status:** Accepted
**Date:** 2026-05-27
**Amended:** 2026-06-01

## Context

AI agents need clear ownership to avoid cross-editing scraper, StokAPI, and n8n router code.

## Decision

| Tier | Path | Scope |
|------|------|--------|
| 1 Platform | `.agent/`, `AGENTS.md`, `docs/` | Router, dual pipeline, contracts, sync |
| 2a Scraper | `scrapers/.agent/` | Playwright, Celery, cache, scraper receiver |
| 2b StokAPI | `muvstok-api/.agent/` | Worker, Muvstok, stokapi receiver (gold standard layout) |
| 3 n8n contracts | `.agent/boundaries/n8n.md` | Webhook paths, workflow IDs |

Scraper skills live in `scrapers/.agent/skills/` (migrated from legacy `.claude/`).

## Consequences

- Platform agents delegate service-deep work to Tier 2 entries.
- `muvstok-api/.agent/` is the template for commands, standards, sub-agents, and skills structure.
- Task-scoped rules live under `.agent/rules/` so agent guidance has one project-owned workspace.
