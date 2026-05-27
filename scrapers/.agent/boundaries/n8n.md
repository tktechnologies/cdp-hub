# Scraper n8n boundaries

## Owns

- `n8n/workflows/cdp_scraper.json` — callback receiver, sheet flatten, Telegram
- `n8n/docs/AI_AGENT_CONTEXT.md`, `n8n/docs/N8N_WORKFLOW_GUIDE.md` (scraper-specific)
- `n8n/settings/` for scraper workflows

## Shares (do not edit alone)

- `n8n/workflows/cdp_router.json` — JSON in this repo; **Code** from `../../n8n/src/`
- Publish all three workflows via monorepo `make sync-n8n`

## Does not own

- `n8n/workflows/cdp_stokapi.json` (monorepo root)
- `n8n/src/router_stokapi.js` (platform)

## Webhook

- Path: `scraper-result` (stable)
- Secret header: `X-Webhook-Secret`
