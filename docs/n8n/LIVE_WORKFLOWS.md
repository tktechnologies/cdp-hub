# CDP n8n — Live workflows

Last verified: 2026-06-02.

| Workflow | Live ID | Webhook / trigger | Role |
|----------|---------|-------------------|------|
| **cdp_router** | `6id6dkinK9xTLfsb` | Telegram, Gmail, schedule | Orchestrator: `.analisar` / `.sku` → Scraper + StokAPI |
| **cdp_scraper** | `VfBSV3WU6on8BXm8` | `POST /webhook/scraper-result` | Scraper job callbacks → sheets + notify |
| **cdp_stokapi** | `t160mzGPYYlJcrjZ` | `POST /webhook/muvstok-result` | Muvstok job callbacks → sheets + notify |
| **cdp_progress** | `V9I6o32XDoPIRarz` | Schedule (`CDP_PROGRESS_INTERVAL_MIN`, default 10) | Proactive Telegram progress while runs are active |

Deprecated: `cdp_muvstok-api_starter` (`PXLHDzRbBVgs8Xl2`) — use `cdp_router` for production dispatch.

## Sync from repo {#sync-from-repo}

```bash
make sync-n8n   # from monorepo root; user approval required for publish
```

Pipeline: inject `n8n/src` → patch receivers → validate SDK → **PUT full graph** via n8n REST API (`scripts/n8n_publish.py`) → MCP `publish_workflow`.

For one-off structural patches that are awkward as full JSON replace, use MCP `update_workflow` `operations` + `publish_workflow`.

Latest publish (2026-06-02): `cdp_router` active `9a312497-3c02-49f6-857c-dfd176a176fc`; `cdp_scraper` active `acdfd664-3d85-4341-a28c-fe03b2a2afb5`; `cdp_stokapi` active `fdfa6140-a735-4442-8c4f-899109967c5d`; `cdp_progress` imported and active `V9I6o32XDoPIRarz` (set `CDP_PROGRESS_WORKFLOW_ID` for `make sync-n8n`).

## Local files

| Workflow | Repo path |
|----------|-----------|
| cdp_router | `n8n/workflows/cdp_router.json` |
| cdp_scraper | `n8n/workflows/cdp_scraper.json` |
| cdp_stokapi | `n8n/workflows/cdp_stokapi.json` |
| cdp_progress | `n8n/workflows/cdp_progress.json` |

Shared router Code node sources: `n8n/src/*.js`

**Phase 1 (complete):** Workflow JSON only at repo root `n8n/`. Legacy docs under `scrapers/n8n/docs/` are deprecated.

## Progress visibility (2026-05-27)

- **On-demand:** Telegram `.status`, `.andamento`, `.progresso` → `cdp_router` polls Scraper + StokAPI job APIs (synced 2026-05-27).
- **Proactive:** import `cdp_progress.json` once in n8n, set `CDP_PROGRESS_WORKFLOW_ID`, then `make sync-n8n` includes it.
- **Registry:** `POST /api/v1/dispatch-runs` on Scraper API (router after dispatch); `cdp_progress` polls `GET …/dispatch-runs/active`.
- **Env:** `CDP_PROGRESS_INTERVAL_MIN=10` (0 = disable), `CDP_PROGRESS_MIN_SKUS=15`, `CDP_PROGRESS_MIN_STEP_PCT=10`, `CDP_PROGRESS_MAX_MESSAGES=6`.
- **Shared JS:** `router_register_run.js`, `router_status_prepare.js`, `router_status.js`, `progress_poll.js`, `progress_format.js` (injected via `sync_workflow_code_from_shared.py`).
