# Platform memory

| File | Use for |
|------|---------|
| [implementation-state.md](implementation-state.md) | **Current** deploy IDs, workflow versions, known gaps |
| [decisions.md](decisions.md) | Durable agent-workspace decisions |

**Rules:** Put volatile ops facts in `implementation-state.md` (snapshot at top). Link to `docs/n8n/LIVE_WORKFLOWS.md` for workflow IDs — do not duplicate long changelogs in prompts.

Point-in-time audit reports should not live here unless they contain durable
state that cannot be captured in `decisions.md`, `implementation-state.md`, or
the owning service workspace.
