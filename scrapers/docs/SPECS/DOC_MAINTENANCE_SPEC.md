# Documentation Maintenance Spec

## Purpose
Keep the project usable by fresh AI agents and human maintainers. Documentation is part of the product, not an afterthought.

## Required Updates
Whenever code changes, update the matching docs in the same turn.

Update:
- `docs/MAINTENANCE_CHECKPOINT.md` when production status, blockers, or handoff facts change.
- `docs/SPECS/SPECS.md` for source-of-truth product, architecture, or rule changes.
- `docs/SPECS/INFRASTRUCTURE_SPEC.md` for Azure, IaC, deployment, or networking changes.
- `docs/SPECS/PROXY_ROTATION_SPEC.md` for proxy, anti-bot, or outbound networking changes.
- `docs/TASKS.md` for project status and next work.
- `docs/CHANGELOG.md` for user-visible or agent-visible changes.
- `docs/SYSTEM_OVERVIEW.md` for architecture or component status changes.
- `docs/PRODUCTION_PLAN.md` for production rollout or deployment changes.
- `.agent/` instructions when agent workflows, rules, or repeated processes change.

## Changelog Format
Use reverse chronological entries with concrete dates:

```markdown
## 2026-05-11
- Added ...
- Changed ...
- Fixed ...
```

## Audit Checklist
Before finishing a maintenance turn:

```bash
git status --short
rg -n "S[t]ripe|C[l]erk|\\.[a]gents|docs/T[K]|0_[r]outer|1_[c]omments|spec1-[i]nstagram|file:/[/]/|docs/video_[a]nalysis|demo_[p]resentation|europe\\.py|S[T]UB" .claude docs src tests scripts README.md
rg -n "print\\(" src
# Validate agent markdown links and paths under scrapers/.agent/
find .agent -name '*.md' | head
```

## AI-Agent Rule
If a code change does not require a docs update, explicitly say why in the final response.
