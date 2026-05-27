# StokAPI ↔ platform boundaries

## StokAPI owns

- `app/` — API, worker, Muvstok client, PostgreSQL models
- `cdp_stokapi` workflow JSON and receiver behavior
- `specs/` planning documents

## Platform owns

- `cdp-app/n8n/src/router_stokapi.js` — job dispatch from router
- `cdp_router.json` sync and triple-workflow publish
- `docs/architecture/DUAL_PIPELINE.md`, `docs/n8n/LIVE_WORKFLOWS.md`

## Do not

- Add Playwright, scrape cache, or Celery to this repo
- Create a standalone n8n sender workflow for production (deprecated starter)
- Edit router Code in monorepo `n8n/src/` (not under this service)

## Callback contract

Changes to callback JSON shape require:

1. `app/schemas/callbacks.py`
2. `cdp_stokapi.json` flatten nodes
3. Coordinated note in platform docs if dual-pipeline metadata changes
