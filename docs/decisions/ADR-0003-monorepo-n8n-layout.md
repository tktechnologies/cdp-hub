# ADR-0003: Consolidated `n8n/` at monorepo root

**Status:** Accepted (Phase 1 complete — 2026-05-27)  
**Date:** 2026-05-27

## Context

Router Code and workflow JSON were split across `scrapers/n8n/`, `muvstok-api/n8n/`, and root `n8n/`, causing duplicate sources of truth.

## Decision

**Canonical layout** at repo root:

```text
n8n/
  src/          # Router Code nodes (edit here)
  lib/          # Receiver helpers
  workflows/    # cdp_router, cdp_scraper, cdp_stokapi, cdp_progress
  settings/
```

Inject script targets `n8n/workflows/cdp_router.json` and `cdp_progress.json`.

## Consequences

- **Phase 1 complete:** Workflow JSON removed from `scrapers/n8n/workflows/` and `muvstok-api/n8n/workflows/`. Only deprecated docs may remain under `scrapers/n8n/docs/`.
- Docs and `.agent/boundaries/n8n.md` list canonical `n8n/` paths only.
- Agents must not treat `scrapers/n8n/shared/dual_dispatch/` as source of truth.
- `make sync-n8n` pushes `cdp_router`, `cdp_scraper`, `cdp_stokapi`; `cdp_progress` is manual import until added to `sync-all-n8n.sh`.
