# CDP n8n — Live workflows

Last verified: 2026-06-06.

Production truth lives in this document. DEV workflow copies run in the same
n8n instance under names prefixed `DEV - ...`; their IDs are tracked in
[.agent/memory/implementation-state.md](../../.agent/memory/implementation-state.md).
Do not use `cdp-n8n-dev` for CDP DEV traffic unless a later approved plan
changes the operating model.

| Workflow | Live ID | Webhook / trigger | Role |
|----------|---------|-------------------|------|
| **cdp_router** | `6id6dkinK9xTLfsb` | Telegram, Gmail, schedule | Orchestrator: `.analisar` / `.sku` → Scraper + StokAPI |
| **cdp_scraper** | `VfBSV3WU6on8BXm8` | `POST /webhook/scraper-result` | Scraper job callbacks → sheets + notify |
| **cdp_stokapi** | `t160mzGPYYlJcrjZ` | `POST /webhook/muvstok-result` | Muvstok job callbacks → sheets + notify |
| **cdp_progress** | `V9I6o32XDoPIRarz` | Schedule (`CDP_PROGRESS_INTERVAL_MIN`, default 10) | Proactive Telegram progress while runs are active |
| **cdp_notifier** | `ennI9nKin9ruPaLO` | `POST /webhook/cdp-notifier` | Single final Telegram/email after both pipelines finish (`delivery_mode: aggregate`) |

Deprecated: `cdp_muvstok-api_starter` (`PXLHDzRbBVgs8Xl2`) — use `cdp_router` for production dispatch.

## Sync from repo {#sync-from-repo}

```bash
make sync-n8n   # from monorepo root; user approval required for publish
make sync-n8n-dev # shared n8n DEV copies; requires CDP_DEV_* workflow IDs
```

Pipeline: inject `n8n/src` → patch receivers → validate SDK → **PUT full graph** via n8n REST API (`scripts/n8n_publish.py`) → MCP `publish_workflow` where available. Non-MCP workflows such as `cdp_progress` are activated via REST fallback.

DEV copies are generated from the same source JSON with
`scripts/generate_dev_n8n_workflows.py`. They use `dev-scraper-result`,
`dev-muvstok-result`, and `dev-cdp-notifier` webhook paths, DEV-prefixed n8n env,
DEV Telegram credential, and DEV Google Sheets IDs.

For one-off structural patches that are awkward as full JSON replace, use MCP `update_workflow` `operations` + `publish_workflow`.

MCP access is enabled for `cdp_router`, `cdp_scraper`, and `cdp_stokapi`.
As of 2026-06-06, MCP access is not enabled for `cdp_progress`,
`cdp_notifier`, or the DEV workflow copies; MCP calls return "Workflow is not
available in MCP" until access is enabled on each workflow card/settings.

Latest full sync (2026-06-05): `cdp_router` `bb52096d-aff9-4895-941b-0391643a75d7` (53 nodes); `cdp_scraper` `67be3cf3-fb6b-425a-a55a-340cb713b5f9` (47 nodes); `cdp_stokapi` `c6eca24d-eefa-4932-90e2-9292614d8667` (19 nodes); `cdp_progress` REST activation (10 nodes; MCP publish unavailable until MCP enabled on workflow card). **Last known active version** per workflow (including targeted publishes that supersede a full sync) is in [.agent/memory/implementation-state.md](../../.agent/memory/implementation-state.md).

Latest MCP publish check (2026-06-06): `cdp_router`
`65dea47b-8cba-4db5-9969-da9493eec252`; `cdp_scraper`
`0086a065-8369-48d3-b33a-4de4312f76f6`; `cdp_stokapi`
`e139b97d-0688-4cf1-ba5a-2899d24dcaac`. MCP validation was valid for all
three workflows.

## Local files

| Workflow | Repo path |
|----------|-----------|
| cdp_router | `n8n/workflows/cdp_router.json` |
| cdp_scraper | `n8n/workflows/cdp_scraper.json` |
| cdp_stokapi | `n8n/workflows/cdp_stokapi.json` |
| cdp_progress | `n8n/workflows/cdp_progress.json` |
| cdp_notifier | `n8n/workflows/cdp_notifier.json` |

Shared router Code node sources: `n8n/src/*.js`

**Phase 1 (complete):** Workflow JSON only at repo root `n8n/`. Legacy docs under `scrapers/n8n/docs/` are deprecated.

## Progress visibility (2026-05-27)

- **On-demand:** Telegram `.status`, `.andamento`, `.progresso` → `cdp_router` polls Scraper + StokAPI job APIs (synced 2026-05-27).
- **Proactive:** import `cdp_progress.json` once in n8n, set `CDP_PROGRESS_WORKFLOW_ID`, then `make sync-n8n` includes it.
- **Registry:** `POST /api/v1/dispatch-runs` on Scraper API (router after dispatch); `cdp_progress` polls `GET …/dispatch-runs/active`.
- **Env:** `CDP_PROGRESS_INTERVAL_MIN=10` (0 = disable), `CDP_PROGRESS_MIN_SKUS=15`, `CDP_PROGRESS_MIN_STEP_PCT=10`, `CDP_PROGRESS_MAX_MESSAGES=6`.
- **Shared JS:** `formatar_payload_scraper.js`, `router_stokapi.js`, `router_register_run.js`, `router_status_prepare.js`, `router_status.js`, `progress_poll.js`, `progress_format.js` (injected via `sync_workflow_code_from_shared.py`).
