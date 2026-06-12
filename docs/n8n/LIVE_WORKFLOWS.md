# CDP n8n — Live workflows

Last verified: 2026-06-12.

Production truth lives in this document. As of the 2026-06-11 STOKAI cutover,
production Telegram/email/schedule traffic is handled by `STOKAI - cdp_router`
and `STOKAI - cdp_progress`; the original `cdp_router` / `cdp_progress` are
inactive rollback workflows. DEV workflow copies run in the same n8n instance
under names prefixed `DEV - ...`; their IDs are tracked in
[.agent/memory/implementation-state.md](../../.agent/memory/implementation-state.md).
Do not use `cdp-n8n-dev` for CDP DEV traffic unless a later approved plan
changes the operating model.

| Workflow | Live ID | State | Webhook / trigger | Role |
|----------|---------|-------|-------------------|------|
| **STOKAI - cdp_router** | `wjwdSgwc2b017mjG` | active | Telegram, Gmail, schedule | Orchestrator: `.analisar` / `.sku` → STOKAI Scraper + StokAPI |
| **STOKAI - cdp_scraper** | `MZVx4YwXrQVy5aua` | active | `POST /webhook/stokai-scraper-result` | STOKAI Scraper job callbacks → sheets + notify |
| **STOKAI - cdp_stokapi** | `IV1756ZgTBL6x7lL` | active | `POST /webhook/stokai-muvstok-result` | STOKAI StokAPI callbacks → sheets + notify |
| **STOKAI - cdp_progress** | `bI2HteRYIvOvGsjN` | active | Schedule (`CDP_STOKAI_PROGRESS_INTERVAL_MIN`, default 10) | Proactive Telegram progress while STOKAI runs are active |
| **STOKAI - cdp_notifier** | `6CUB7JFG5Jy5D09z` | active | `POST /webhook/stokai-cdp-notifier` | Single final Telegram/email after both STOKAI pipelines finish |
| `cdp_router` | `6id6dkinK9xTLfsb` | inactive rollback | Telegram, Gmail, schedule | Original automation router |
| `cdp_progress` | `V9I6o32XDoPIRarz` | inactive rollback | Schedule | Original automation progress |
| `cdp_scraper` | `VfBSV3WU6on8BXm8` | active rollback receiver | `POST /webhook/scraper-result` | Original Scraper job callbacks |
| `cdp_stokapi` | `t160mzGPYYlJcrjZ` | active rollback receiver | `POST /webhook/muvstok-result` | Original StokAPI callbacks |
| `cdp_notifier` | `ennI9nKin9ruPaLO` | active rollback notifier | `POST /webhook/cdp-notifier` | Original aggregate notifier |

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

STOKAI copies are generated from the same source JSON with
`make n8n-stokai-workflows`. They use `stokai-scraper-result`,
`stokai-muvstok-result`, and `stokai-cdp-notifier` webhook paths, plus
`CDP_STOKAI_*` n8n env vars. Import with `make import-n8n-stokai`; after
direct STOKAI price smokes and receiver callback smokes pass, cut over by
deactivating original `cdp_router` / `cdp_progress` and activating
`STOKAI - cdp_router` / `STOKAI - cdp_progress`. Record imported workflow IDs
in [.agent/memory/implementation-state.md](../../.agent/memory/implementation-state.md).

Latest STOKAI cutover (2026-06-11): original `cdp_router`
`6id6dkinK9xTLfsb` and `cdp_progress` `V9I6o32XDoPIRarz` deactivated;
`STOKAI - cdp_router` `wjwdSgwc2b017mjG` and `STOKAI - cdp_progress`
`bI2HteRYIvOvGsjN` activated. Pre-cutover callback smoke succeeded with
executions `3531` (`STOKAI - cdp_scraper`), `3532` (`STOKAI - cdp_stokapi`),
and `3533` (`STOKAI - cdp_notifier`).

Latest STOKAI Sheets endpoint rollback (2026-06-12): active STOKAI router,
scraper receiver, StokAPI receiver, and notifier were patched directly via n8n
REST + REST reactivation fallback to use the approved workbook IDs
`1IGhsIhrwlnMaCduR-W-eIi9O4mMO2pPYjE-tefgIPII` (SKUs; tab selected by name) and
`1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo` (Resultados; report link
`gid=2127243308`). Verification rerun was idempotent (`0/4` changed), and
`cdp-n8n-prod` has no `CDP_RESULTADOS_SHEETS_URL` override.

Latest STOKAI email recovery (2026-06-12): Gmail `.analisar` execution `3856`
started Scraper job `2b5bc112-faa1-4fff-a862-656d4deb495b` for batch
`bg-mqb7jdkx-92hyo0`, but API Diversos dispatch returned `401 Invalid API key`
because `cdp-stokai-muv-api` still had a stale 32-character `api-keys`
Container App secret while Key Vault/n8n used the current 64-character
`api-key`. The API app secret was refreshed from `cdp-stokai-kv-prod`, the
active API revision was restarted, and an authenticated probe returned `404`
for a nonexistent job (auth accepted). The missing API Diversos arm was resumed
as job `d1db1a02-cb0b-4151-a939-c37143f46598`; receiver execution `3876` and
notifier execution `3877` succeeded, and the dispatch run was patched to
`final_notification_status=sent`, `final_channel=email`. `STOKAI - cdp_notifier`
was updated by REST + REST reactivation fallback so `PATCH final-notification`
uses `CDP_STOKAI_SCRAPER_API_BASE` / `CDP_STOKAI_API_KEY` (MCP still disabled
on the workflow card). The same incident exposed silent execution `3853`, where
`📊 Ler CDP_SKUs` returned 0 rows and the router ended without replying. The live
`STOKAI - cdp_router` was updated by REST + REST reactivation fallback so the
sheet read always emits an empty item, DQ treats that item as 0 rows, the
confirmation branch replies with `Consulta CDP sem peças pendentes`, and API
Diversos error formatting unwraps object-shaped errors instead of rendering
`[object Object]`. Live read-back confirmed the router is active with
`alwaysOutputData`, DQ blank filtering, empty reply text, and `compactError`.

Latest repo sync (2026-06-12): `make sync-n8n-dev` and
`make sync-n8n-stokai` published all DEV and STOKAI workflow copies through
n8n REST, with REST reactivation fallback because MCP is not enabled on those
workflow cards. Read-back confirmed all five DEV workflows and all five STOKAI
workflows are active with expected node counts. The original rollback
`cdp_router` and `cdp_progress` remained inactive; rollback
`cdp_scraper`, `cdp_stokapi`, and `cdp_notifier` remained active.

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
