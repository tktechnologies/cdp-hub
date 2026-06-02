# Platform agent decisions

Durable choices for CDP agent architecture. Update when conventions change. ADRs: [docs/decisions/](../../docs/decisions/).

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-26 | Three-tier agents: platform / service / n8n | Clear ownership; avoids duplicating skills |
| 2026-05-26 | `n8n/src/` is sole router Code source | Single inject path into `cdp_router.json` |
| 2026-05-27 | Scraper skills in `scrapers/.agent/skills/` | Migrated from legacy `.claude/`; single workspace |
| 2026-05-26 | StokAPI skills in `muvstok-api/.agent/skills/` | Gold-standard layout for commands, sub-agents, standards |
| 2026-05-26 | `make sync-n8n` publishes router + receivers | Receivers and router stay in sync |
| 2026-05-26 | No Execute Workflow for StokAPI | Inline HTTP in router only |
| 2026-05-27 | Canonical n8n at repo root `n8n/` | Phase 1 retires `scrapers/n8n/` duplicates when complete |
| 2026-05-27 | Root repo is the canonical CDP monorepo | `scrapers/` and `muvstok-api/` are first-class folders; old nested Git histories backed up under `.git-boundary-backups/` |
| 2026-05-26 | AIOX workflows excluded from CDP runtime | `.agent/workflows/*.md` top level = IDE personas |
| 2026-06-01 | Task-scoped agent rules live in `.agent/rules/` | Keep project-owned agent guidance under `.agent/` instead of a separate IDE rule tree |
| 2026-06-01 | Root `.agent/knowledge/` is the service catalog layer | Keep n8n/API/Scraper ownership synchronized without copying service internals |
