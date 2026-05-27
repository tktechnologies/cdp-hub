# StokAPI n8n boundaries

## Owns

- `n8n/workflows/cdp_stokapi.json` — callback receiver, sheets, Telegram
- `n8n/docs/MUVSTOK_N8N_WORKFLOW_GUIDE.md`
- `n8n/settings/cdp_stokapi.json`

## Does not own

- `cdp_router` dispatch (platform: `n8n/src/router_stokapi.js`)
- `cdp_scraper.json` (scraper service)

## Webhook

- Path: `muvstok-result` (stable)
- Header: `x-webhook-secret`

## Publish

All three workflows publish together: monorepo `make sync-n8n` (user approval). Do not push receiver alone unless documented exception.
