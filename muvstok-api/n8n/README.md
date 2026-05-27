# n8n (moved)

StokAPI receiver workflow and shared libs are at the **monorepo root**:

- `../../n8n/workflows/cdp_stokapi.json`
- `../../n8n/lib/muvstok_*.js`
- Router dispatch: `../../n8n/src/router_stokapi.js` (in `cdp_router`)

Guide: [docs/MUVSTOK_N8N_WORKFLOW_GUIDE.md](docs/MUVSTOK_N8N_WORKFLOW_GUIDE.md)

Sync: `make sync-n8n` from repo root (requires user approval to publish).
