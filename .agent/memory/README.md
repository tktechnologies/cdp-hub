# Platform memory

| File | Use for |
|------|---------|
| [implementation-state.md](implementation-state.md) | **Current** deploy IDs, workflow versions, known gaps |
| [decisions.md](decisions.md) | Durable agent-workspace decisions |
| `agent-workspace-audit-*.md` | Point-in-time audits (historical) |

**Rules:** Put volatile ops facts in `implementation-state.md` (snapshot at top). Link to `docs/n8n/LIVE_WORKFLOWS.md` for workflow IDs — do not duplicate long changelogs in prompts.
