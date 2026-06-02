# Agent Workspace Audit - 2026-05-27

Scope: root `.agent/`, `scrapers/.agent/`, `muvstok-api/.agent/`, root/service `AGENTS.md`, task-scoped agent rules, and the canonical platform docs that agent guidance depends on.

Superseded note (2026-06-01): task-scoped rules now live in `.agent/rules/`, the short quality-gate command doc was collapsed into `run-quality-gates.md`, and `cdp_progress` is included by `make sync-n8n` once `CDP_PROGRESS_WORKFLOW_ID` is set.

## Inventory

| Area | Files reviewed | Role |
|------|----------------|------|
| `.agent/` | 38 | Tier 1 platform routing, skills, prompts, commands, standards, memory |
| `scrapers/.agent/` | 23 | Tier 2a scraper guidance |
| `muvstok-api/.agent/` | 47 | Tier 2b StokAPI guidance |
| `.agent/rules/` | 7 | Task-scoped rule summaries |

## Current Shape

- Canonical platform entry is `AGENTS.md` -> `docs/ARCHITECTURE.md` -> `docs/n8n/LIVE_WORKFLOWS.md` -> `.agent/index.md`.
- `docs/PLATFORM_OVERVIEW.md` remains useful as the detailed API/Azure reference, not the first bootstrap source.
- n8n source of truth is clear: edit `n8n/src/*.js`, inject with `python3 scripts/sync_workflow_code_from_shared.py`, publish with `make sync-n8n` only after explicit user approval.
- Service ownership is clear: scraper owns Playwright/Celery/cache and `cdp_scraper`; StokAPI owns Redis Streams/Muvstok/API Diversos and `cdp_stokapi`.
- Superseded 2026-06-01: `cdp_progress` still needs a first import/live ID, but `make sync-n8n` includes it once `CDP_PROGRESS_WORKFLOW_ID` is set.

## Fixes Applied

- Removed stale "max 5 SKUs" guidance from platform rules, n8n prompt, dual-pipeline skill, release checklist, and agent architecture. Current behavior is all valid SKUs by default, with optional `CDP_DISPATCH_SAMPLE_SIZE` sampling.
- Fixed broken scraper agent links from nested prompt/skill files to root `docs/` and root `.agent/`.
- Fixed task-rule Markdown links so they resolve from their workspace.
- Updated StokAPI guidance that still said tests were not implemented; current state has unit, service, and contract tests.
- Replaced the active `CLAUDE.md` scraper rule reference with current `docs/SCRAPER_FIELD_GUIDE.md` / `src/models/schemas.py`.
- Updated quality-gate notes for existing root `make test-all` and the placeholder status of StokAPI infra.
- Clarified the agent-workspace maintenance prompt: historical `.claude/` mentions in changelogs/ADRs are allowed; active guidance should not point there.

## Verification

- Markdown link check across 106 root/service agent files: 143 local links checked, 0 broken.
- Task-rule link check across 7 files: 0 broken.
- Stale-pattern scan across agent and canonical docs for `max 5`, `SKU limit (5)`, `tests not yet implemented`, `not implemented beyond`, and `CLAUDE.md`: 0 active hits outside this audit report.
- No application code changed and no tests were run; this was documentation/agent-context maintenance.
- No live n8n publish was performed.

## Remaining Simplification Opportunities

1. Set `CDP_PROGRESS_WORKFLOW_ID` after first import so `cdp_progress` is included in `make sync-n8n`.
2. Archive or stub deprecated legacy n8n docs under `scrapers/n8n/docs/` so search results are quieter for new agents.
3. Consider a shorter StokAPI quickstart in front of the 47-file workspace. The routing is good, but the volume is high compared with platform and scraper.
4. Keep service startup prompts pointed at canonical `docs/ARCHITECTURE.md` first, with `PLATFORM_OVERVIEW.md` only as the detailed reference.
