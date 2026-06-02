# Scraper n8n boundaries

Workflow JSON lives at the **monorepo root** (`n8n/workflows/`), not under `scrapers/`.

Paths below are monorepo-root paths unless they are Markdown links.

## Owns

- `n8n/workflows/cdp_scraper.json` — callback receiver, sheet flatten, Telegram
- `n8n/lib/` — scraper receiver helpers (e.g. Telegram notification)
- Scraper-specific guides: `scrapers/docs/`, `scrapers/.agent/skills/n8n-*`

## Shares (platform)

- `n8n/workflows/cdp_router.json` — router JSON; **Code** from `n8n/src/`
- Publish: monorepo `make sync-n8n` (see `.agent/skills/n8n-router-sync/SKILL.md`)

## Does not own

- `n8n/workflows/cdp_stokapi.json` — StokAPI / API Diversos receiver
- `n8n/src/router_stokapi.js` and other router-only `n8n/src/*.js`

## Webhook

- Path: `scraper-result` (stable)
- Secret header: `X-Webhook-Secret`

## Canonical docs

- [../../../docs/n8n/LIVE_WORKFLOWS.md](../../../docs/n8n/LIVE_WORKFLOWS.md)
- [../../../docs/n8n/WORKFLOW_GUIDE.md](../../../docs/n8n/WORKFLOW_GUIDE.md)
