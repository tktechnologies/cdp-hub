# CDP n8n — Live workflows

Last verified: 2026-05-29.

| Workflow | Live ID | Webhook / trigger | Role |
|----------|---------|-------------------|------|
| **cdp_router** | `6id6dkinK9xTLfsb` | Telegram, Gmail, schedule | Orchestrator: `.analisar` / `.sku` → Scraper + StokAPI |
| **cdp_scraper** | `VfBSV3WU6on8BXm8` | `POST /webhook/scraper-result` | Scraper job callbacks → sheets + notify |
| **cdp_stokapi** | `t160mzGPYYlJcrjZ` | `POST /webhook/muvstok-result` | Muvstok job callbacks → sheets + notify |
| **cdp_progress** | _(import from repo — not in `make sync-n8n` yet)_ | Schedule (`CDP_PROGRESS_INTERVAL_MIN`, default 10) | Proactive Telegram progress while runs are active |

Deprecated: `cdp_muvstok-api_starter` (`PXLHDzRbBVgs8Xl2`) — use `cdp_router` for production dispatch.

## Sync from repo

```bash
make sync-n8n   # from monorepo root; user approval required for publish
```

> ⚠️ **Known limitation (2026-05-29):** `make sync-n8n` runs the patch scripts (repo JSON stays correct) and re-publishes, but the `update_workflow` call in `scrapers/scripts/push_workflow_mcp.py` is **code-based** and the current MCP `update_workflow` only accepts `operations` — so the live **graph is not updated** by sync. The pusher now fails loudly when this happens. Until it is rewritten to diff→`operations`, apply structural workflow changes via `update_workflow` `operations` + `publish_workflow` (see `.agent/memory/implementation-state.md`). The duplicate-SKU `row_number` writeback fix (both receivers) was applied this way on 2026-05-29.

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
- **Proactive:** import `cdp_progress.json` in n8n, set schedule env, activate — not pushed by `sync-all-n8n.sh` yet.
- **Registry:** `POST /api/v1/dispatch-runs` on Scraper API (router after dispatch); `cdp_progress` polls `GET …/dispatch-runs/active`.
- **Env:** `CDP_PROGRESS_INTERVAL_MIN=10` (0 = disable), `CDP_PROGRESS_MIN_SKUS=15`, `CDP_PROGRESS_MIN_STEP_PCT=10`, `CDP_PROGRESS_MAX_MESSAGES=6`.
- **Shared JS:** `router_register_run.js`, `router_status_prepare.js`, `router_status.js`, `progress_poll.js`, `progress_format.js` (injected via `sync_workflow_code_from_shared.py`).
