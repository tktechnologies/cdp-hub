# Agent Startup

Use at the start of any fresh AI-agent chat for this repository.

**Platform bootstrap:** [`.agent/prompts/new-chat.md`](../../../.agent/prompts/new-chat.md) (monorepo-wide).

**Typed maintenance sessions:** [`.agent/prompts/maintenance/`](../../../.agent/prompts/maintenance/README.md) (scraper, n8n, infra, etc.).

## Bootstrap (do these first)

1. Read `.agent/index.md` and `.agent/rules.md`.
2. Read `docs/MAINTENANCE_CHECKPOINT.md` and `.agent/memory/implementation-state.md` (scraper runtime only — n8n IDs: root `.agent/memory/implementation-state.md`).
3. `git status --short` — never revert user changes.

## Classify the task

| Task | Skill / doc |
|------|-------------|
| Site scraper | `skills/scraper-implementation/SKILL.md` |
| Debug failure | `skills/scraper-debugging/SKILL.md` |
| API / schema | `skills/api-endpoint/SKILL.md` |
| n8n receiver | `skills/n8n-audit/SKILL.md` |
| Router / dual pipeline | Platform `../../.agent/prompts/maintenance/n8n.md` |

## Working rules

- Act like a senior engineer; small, testable changes.
- Update docs in the same turn as code changes.
- Never commit credentials, browser state, or customer data.
- `make test lint` before marking scraper work done.

## End of turn

Summarize what changed, what was verified, risks, and next step.
