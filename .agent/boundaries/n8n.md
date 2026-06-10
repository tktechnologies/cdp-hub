# n8n boundaries

> **Canonical live IDs:** this file, [memory/implementation-state.md](../memory/implementation-state.md), and [docs/n8n/LIVE_WORKFLOWS.md](../../docs/n8n/LIVE_WORKFLOWS.md). Service `.agent/memory/` files must link here — do not copy ID tables.

## Production workflows

| Name | ID | Canonical repo file | Dispatch / receive |
|------|-----|---------------------|-------------------|
| `cdp_router` | `6id6dkinK9xTLfsb` | `n8n/workflows/cdp_router.json` | **Dispatches** both APIs; `.status` / `.andamento` |
| `cdp_scraper` | `VfBSV3WU6on8BXm8` | `n8n/workflows/cdp_scraper.json` | Receives `scraper-result` |
| `cdp_stokapi` | `t160mzGPYYlJcrjZ` | `n8n/workflows/cdp_stokapi.json` | Receives `muvstok-result` |
| `cdp_progress` | `V9I6o32XDoPIRarz` | `n8n/workflows/cdp_progress.json` | Schedule: proactive progress Telegram |
| `cdp_notifier` | `ennI9nKin9ruPaLO` | `n8n/workflows/cdp_notifier.json` | Receives receiver handoff → single aggregate final notification |

`make sync-n8n` pushes router + receivers + progress + notifier via
`scripts/n8n_publish.py` (REST) when the corresponding workflow IDs are
exported. Set `CDP_PROGRESS_WORKFLOW_ID` and `CDP_NOTIFIER_WORKFLOW_ID` to
include progress and notifier workflows.

## Service-specific n8n docs

- `muvstok-api/n8n/docs/` — StokAPI receiver operations only; workflow JSON at monorepo `n8n/workflows/`
- Platform n8n docs: `docs/n8n/`, `n8n/README.md`

**Source of truth:** `n8n/src/` and `n8n/workflows/`. Do not edit removed legacy JSON copies.

## Router + progress Code nodes (edit here only)

| File | Node purpose |
|------|----------------|
| `n8n/src/router_limitar_skus.js` | Optional sample (`CDP_DISPATCH_SAMPLE_SIZE`, default 0 = all) |
| `n8n/src/router_dq.js` | Normalize, validate, and deduplicate dispatch SKUs |
| `n8n/src/router_save_context.js` | Persist router context for downstream branches |
| `n8n/src/formatar_payload_scraper.js` | Scraper `POST /api/v1/jobs` bodies |
| `n8n/src/router_stokapi.js` | StokAPI `POST /api/v1/muvstok/jobs` |
| `n8n/src/emparelhar_scraper.js` | Sheet `PROCESSADO` (merge with `📊 Ler CDP_SKUs` + `pairedItem`) |
| `n8n/src/notifier_expandir_notificado.js` | Notifier: collapse row_numbers for `NOTIFICADO` |
| `n8n/src/notifier_mapear_notificado.js` | Notifier: merge `NOTIFICADO` onto sheet read rows |
| `n8n/src/router_error_scraper.js` | Scraper dispatch errors |
| `n8n/src/router_error_stokapi.js` | StokAPI dispatch errors |
| `n8n/src/router_confirmacao.js` | Dispatch confirmation message |
| `n8n/src/router_telegram.js` | Command router (`.analisar`, `.sku`, `.status`, …) |
| `n8n/src/router_register_run.js` | Persist run + `POST /api/v1/dispatch-runs` |
| `n8n/src/router_status_prepare.js` | Resolve active run for status command |
| `n8n/src/router_status.js` | Format dual-pipeline status reply |
| `n8n/src/progress_poll.js` | `cdp_progress`: list active runs, fetch thresholds |
| `n8n/src/progress_format.js` | `cdp_progress`: format message + PATCH run |

Inject: `python3 scripts/sync_workflow_code_from_shared.py` (router +
`cdp_progress.json`). `cdp_notifier` is built from
`scripts/build_cdp_notifier_workflow.py`; receiver handoff nodes are patched by
`scripts/patch_receiver_notifier_handoff.py`.

## Rules

1. **Never** use n8n Execute Workflow to call StokAPI in production — inline HTTP in router only.
2. **Never** rename webhooks without deploying API callback URLs and updating both services.
3. **Always** inject shared JS before pushing router: `python3 scripts/sync_workflow_code_from_shared.py`.
4. **Publish** via `make sync-n8n` only with explicit user approval.
5. Scraper dispatch uses `force_refresh: false` — Redis cache (24h TTL) serves repeat SKUs; router does not bypass cache unless `force_refresh: true`.
6. Telegram nodes: set `additionalFields.appendAttribution: false` (no “sent automatically with n8n” footer). Final notifier message omits internal warning lines (blocked/timeout) for end users.
7. Sheet robot columns (D–F): always read → remap with `pairedItem` → update by `row_number`; see `.agent/knowledge/google-sheets-reporting.md`.
8. **Progress env** (n8n): `CDP_PROGRESS_INTERVAL_MIN` (0 = off), `CDP_PROGRESS_MIN_SKUS`, `CDP_PROGRESS_MIN_STEP_PCT`, `CDP_PROGRESS_MAX_MESSAGES`.

## Deprecated

- `cdp_muvstok-api_starter` (`PXLHDzRbBVgs8Xl2`)
- Legacy names `cdp_analise` / `cdp_resultado` (renamed to `cdp_router` / `cdp_scraper`)
- `muvstok_job_sender.json` / `muvstok_job_receiver.json`

## MCP

Use n8n MCP for live inspection. Local JSON + `n8n/src/` are the edit source of truth.
