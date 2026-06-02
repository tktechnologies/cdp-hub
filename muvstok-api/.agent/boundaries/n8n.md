# StokAPI n8n boundaries

Workflow JSON lives at the **monorepo root** (`n8n/workflows/`), not under `muvstok-api/`.

Paths below are monorepo-root paths unless they are Markdown links.

## Owns

- `n8n/workflows/cdp_stokapi.json` — callback receiver (`muvstok-result`)
- `n8n/lib/` — shared receiver helpers used by stokapi workflow
- `muvstok-api/n8n/docs/MUVSTOK_N8N_WORKFLOW_GUIDE.md` — receiver operations (not workflow JSON)

## Shares (platform)

- `n8n/workflows/cdp_router.json` — production dispatch via `n8n/src/router_stokapi.js`
- Publish: monorepo `make sync-n8n`

## Does not own

- `n8n/workflows/cdp_scraper.json`
- Router-only files under `n8n/src/` except coordination on `router_stokapi.js` (platform-owned)

## Webhook

- Path: `muvstok-result` (stable)

## Canonical docs

- [../../../docs/n8n/LIVE_WORKFLOWS.md](../../../docs/n8n/LIVE_WORKFLOWS.md)
