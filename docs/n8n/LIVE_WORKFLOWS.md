# CDP n8n — Live workflows

Last verified: 2026-06-10.

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
| **cdp_notifier** | `ennI9nKin9ruPaLO` | `POST /webhook/cdp-notifier` | Single final Telegram/email after both pipelines finish; email includes job-scoped CSV (`delivery_mode: aggregate`) |

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
As of 2026-06-09, MCP access is not enabled for `cdp_progress`,
`cdp_notifier`, or the DEV workflow copies; MCP calls return "Workflow is not
available in MCP" until access is enabled on each workflow card/settings.

Latest targeted sync (2026-06-09): exact SKUs robot-header writeback +
blocked-site deactivation — `cdp_router`
`e0303e69-3b0f-4ea1-a970-707ca32eeaf7` (53 nodes; dispatch sites now
`gm,ml,vw,eu,melibox`); `cdp_scraper`
`39f2706f-333c-4f7b-b8fb-4095463db2db` (49 nodes); `cdp_stokapi`
`e24e2a30-f67f-42b2-8c18-bac97772cdba` (21 nodes); `cdp_progress` REST
update/reactivate; `cdp_notifier` REST update/reactivate (15 nodes; exact
`NOTIFICADO 🤖` header). Prior targeted sync: router `199b21e3`, scraper
`b66066f4`, stokapi `da621eb6`. **Last known active version** per workflow is in
[.agent/memory/implementation-state.md](../../.agent/memory/implementation-state.md).

Latest callback smoke (2026-06-09): batch
`bg-codex-positive-20260609134721` produced successful n8n executions
`2356` (`cdp_scraper`), `2355` (`cdp_stokapi`), and `2358`
(`cdp_notifier`). The notifier `pipeline-result` response had
`both_terminal=true` and `ready_for_final=true`; the controlled smoke had no
Telegram/email target, so final delivery was patched without sending a user
message.

Latest Telegram delivery evidence (2026-06-08): `cdp_notifier` execution
`2067` for batch `bg-mq5kmekg-2iiivj` ran `📱 Telegram: resultado final` and
patched `final_channel=telegram` with no final error.

Latest DEV sync (2026-06-09): `DEV - cdp_router`, `DEV - cdp_scraper`,
`DEV - cdp_stokapi`, `DEV - cdp_progress`, and `DEV - cdp_notifier` were
updated by REST PUT and reactivated through REST fallback. Smoke POSTs to
`dev-scraper-result`, `dev-muvstok-result`, and `dev-cdp-notifier` returned
HTTP 200.

## Local files

| Workflow | Repo path |
|----------|-----------|
| cdp_router | `n8n/workflows/cdp_router.json` |
| cdp_scraper | `n8n/workflows/cdp_scraper.json` |
| cdp_stokapi | `n8n/workflows/cdp_stokapi.json` |
| cdp_progress | `n8n/workflows/cdp_progress.json` |
| cdp_notifier | `n8n/workflows/cdp_notifier.json` |

Shared router Code node sources: `n8n/src/*.js`

**Phase 1–2 (complete):** Workflow JSON only at repo root `n8n/`. Legacy `scrapers/n8n/` redirect stubs removed.

## Progress visibility (2026-05-27)

- **On-demand:** Telegram `.status`, `.andamento`, `.progresso` → `cdp_router` polls Scraper + StokAPI job APIs (synced 2026-05-27).
- **Proactive:** import `cdp_progress.json` once in n8n, set `CDP_PROGRESS_WORKFLOW_ID`, then `make sync-n8n` includes it.
- **Registry:** `POST /api/v1/dispatch-runs` on Scraper API (router after dispatch); `cdp_progress` polls `GET …/dispatch-runs/active`.
- **Env:** `CDP_PROGRESS_INTERVAL_MIN=10` (0 = disable), `CDP_PROGRESS_MIN_SKUS=15`, `CDP_PROGRESS_MIN_STEP_PCT=10`, `CDP_PROGRESS_MAX_MESSAGES=6`.
- **Shared JS:** `formatar_payload_scraper.js`, `router_stokapi.js`, `router_register_run.js`, `router_status_prepare.js`, `router_status.js`, `progress_poll.js`, `progress_format.js` (injected via `sync_workflow_code_from_shared.py`).
