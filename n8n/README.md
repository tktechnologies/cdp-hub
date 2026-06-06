# CDP n8n Workflows

Single source of truth for n8n router code, workflow JSON, and receiver helpers.

Agent entry: [AGENTS.md](AGENTS.md) redirects n8n work to the platform `.agent`
workspace.

## Layout

| Path | Purpose |
|------|---------|
| `src/` | Router/progress Code node JavaScript (edit here) |
| `lib/` | Receiver helpers (Telegram, Sheets) |
| `workflows/` | Compiled PROD workflow JSON plus DEV copies under `workflows/dev/` |
| `settings/` | Active workflow settings JSON |
| `sdk/` | Generated TypeScript for MCP push (`make sync-n8n`) |

## Sync pipeline

```bash
# Inject src/*.js into workflow JSON, then push to live n8n (requires approval)
make sync-n8n
```

Steps: `scripts/sync_workflow_code_from_shared.py` → patch receivers/build
notifier → `scripts/n8n_publish.py` (REST) → MCP publish where available.

See [docs/n8n/LIVE_WORKFLOWS.md](../docs/n8n/LIVE_WORKFLOWS.md) for workflow
IDs and optional sync IDs (`CDP_PROGRESS_WORKFLOW_ID`,
`CDP_NOTIFIER_WORKFLOW_ID`, and DEV `CDP_DEV_*_WORKFLOW_ID` values).

## Rules

- Edit router logic in `src/` only — never edit embedded code in JSON by hand.
- Never publish live n8n without explicit user approval.
- Deprecated: `cdp_analise`, `cdp_resultado`, `muvstok_job_sender`, `muvstok_job_receiver`.
