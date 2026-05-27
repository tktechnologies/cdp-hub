# CDP n8n Workflows

Single source of truth for n8n router code, workflow JSON, and receiver helpers.

## Layout

| Path | Purpose |
|------|---------|
| `src/` | Router Code node JavaScript (edit here) |
| `lib/` | Receiver helpers (Telegram, Sheets) |
| `workflows/` | Compiled workflow JSON (injected + synced to n8n) |
| `settings/` | Active workflow settings JSON |
| `sdk/` | Generated TypeScript for MCP push (`make sync-n8n`) |

## Sync pipeline

```bash
# Inject src/*.js into workflow JSON, then push to live n8n (requires approval)
make sync-n8n
```

Steps: `scripts/sync_workflow_code_from_shared.py` → patch receivers → MCP push.

## Production workflows

| Workflow | ID | Webhook |
|----------|-----|---------|
| `cdp_router` | `6id6dkinK9xTLfsb` | Telegram, Gmail, schedule |
| `cdp_scraper` | `VfBSV3WU6on8BXm8` | `scraper-result` |
| `cdp_stokapi` | `t160mzGPYYlJcrjZ` | `muvstok-result` |
| `cdp_progress` | _(import manually)_ | Schedule |

See [docs/n8n/LIVE_WORKFLOWS.md](../docs/n8n/LIVE_WORKFLOWS.md).

## Rules

- Edit router logic in `src/` only — never edit embedded code in JSON by hand.
- Never publish live n8n without explicit user approval.
- Deprecated: `cdp_analise`, `cdp_resultado`, `muvstok_job_sender`, `muvstok_job_receiver`.
