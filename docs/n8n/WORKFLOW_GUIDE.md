# n8n Workflow Guide

## Source of truth

| Artifact | Location |
|----------|----------|
| Router Code | `n8n/src/*.js` |
| Workflow JSON | `n8n/workflows/*.json` |
| Receiver helpers | `n8n/lib/` |

## Edit router behavior

1. Edit the relevant file in `n8n/src/` (see [LIVE_WORKFLOWS.md](LIVE_WORKFLOWS.md) for node mapping).
2. Inject into JSON: `python3 scripts/sync_workflow_code_from_shared.py`
3. Review `n8n/workflows/cdp_router.json` diff.
4. Publish: `make sync-n8n` — **only with user approval**.

Publishing uses `scripts/n8n_publish.py` (n8n REST API for the full graph, then MCP `publish_workflow`). See [LIVE_WORKFLOWS.md](LIVE_WORKFLOWS.md#sync-from-repo).

## Dual pipeline

`.analisar` and `.sku` dispatch **Scraper + StokAPI in parallel** from `cdp_router`. StokAPI uses inline HTTP (`router_stokapi.js`), not Execute Workflow.

## Receivers

| Workflow | Webhook | Owner |
|----------|---------|-------|
| `cdp_scraper` | `scraper-result` | Scraper results → Sheets + Telegram |
| `cdp_stokapi` | `muvstok-result` | StokAPI results → Sheets + Telegram |

## Deprecated

Do not use: `cdp_analise`, `cdp_resultado`, `muvstok_job_sender`, `muvstok_job_receiver`.
