# Scraper agent index

## Always read first

1. `rules.md`
2. `memory/implementation-state.md` (scraper runtime — not live n8n IDs)
3. `docs/MAINTENANCE_CHECKPOINT.md`

If the task touches **router** or **both pipelines**, switch to platform tier: [../../.agent/index.md](../../.agent/index.md).

## Task routing

| Task | Read / use |
|------|------------|
| Implement or fix a site scraper | `skills/scraper-implementation/SKILL.md`, `src/scrapers/`, `docs/scrapers/` |
| Debug scrape failure | `skills/scraper-debugging/SKILL.md`, `docs/SCRAPER_FIELD_GUIDE.md` |
| API route, schema, callback | `skills/api-endpoint/SKILL.md`, `src/models/schemas.py`, `src/api/routes/` |
| Orchestrator, cache, jobs | `src/services/orchestrator.py`, `src/services/scrape_cache.py`, `docs/SPECS/SCRAPE_CACHE_SPEC.md` |
| n8n scraper receiver audit | `skills/n8n-audit/SKILL.md`, `../../n8n/workflows/cdp_scraper.json` |
| n8n publish preflight | `skills/n8n-release-preflight/SKILL.md` |
| Router / dual pipeline / platform workflow sync | **Platform** `../../.agent/skills/n8n-router-sync/SKILL.md` |
| BR ISP proxy purchase / prod config | `workflows/proxy-rollout.md`, `commands/proxy-readiness.md` |
| Local dev setup | `workflows/local-development.md`, `docs/LOCAL_VALIDATION.md` |
| Pre-release scraper check | `workflows/scraper-release-check.md` |
| Repo cleanup | `skills/repo-hygiene/SKILL.md` |

## Delegation

Use [sub-agents/](sub-agents/) only when the user explicitly asks for
delegation or parallel agent work.

## Commands (`commands/`)

| Command file | Use |
|--------------|-----|
| `implement-scraper.md` | New site implementation |
| `debug-scraper.md` | Failure investigation |
| `proxy-readiness.md` | Validate proxy before supplier scrapes |
| `add-test.md` | Test additions |
| `start-maintenance-chat.md` | Maintenance session |

## Completion

- Run `make test` (or targeted pytest) for behavior changes
- Update `docs/CHANGELOG.md` when user-facing; use `docs/MAINTENANCE_CHECKPOINT.md` for handoff
- Router Code → platform `n8n/src/`
- Update `memory/implementation-state.md` if production facts changed
