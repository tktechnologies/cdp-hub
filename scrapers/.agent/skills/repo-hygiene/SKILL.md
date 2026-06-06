---
name: scraper-repo-hygiene
description: Clean, audit, or reorganize the scraper repository while preserving useful docs, tests, scripts, and agent guidance.
---

# Skill: Scraper Repo Hygiene

Use when cleaning, auditing, or reorganizing the repository.

## Keep

- `src/` — scraper API code
- `tests/` — scraper, API, service, persistence tests
- `alembic/` — database migrations
- `docs/` — operational docs, specs, scraper playbooks
- `scripts/` — deploy, validate, operate scripts
- `n8n/` — CDP scraper workflow exports and docs
- `.agent/` — agent instructions

## Remove

- Video/presentation artifacts
- Completed one-off task prompts
- Generic cloud notes unrelated to scraper ops
- Workflow exports from external systems
- Dead scripts that don't operate this project

## Workflow

1. `git status --short` — never revert user changes.
2. Group files by purpose.
3. Read suspicious files before deleting.
4. Prefer deleting clearly useless files; update stale-but-useful files.
5. After cleanup, run stale reference search:
   ```bash
   rg -n "S[t]ripe|C[l]erk|\\.[a]gents|docs/T[K]|0_[r]outer|1_[c]omments|spec1-[i]nstagram|file:/[/]/|docs/video_[a]nalysis|demo_[p]resentation|S[T]UB" .agent docs src tests scripts README.md
   rg -n "print\\(" src
   ```
6. Summarize removals and remaining suggestions.
