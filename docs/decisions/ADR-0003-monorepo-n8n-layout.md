# ADR-0003: Consolidated `n8n/` at monorepo root

**Status:** Accepted (Phase 1 complete — 2026-05-27)  
**Date:** 2026-05-27

## Context

Router Code and workflow JSON were split across `scrapers/n8n/`, `muvstok-api/n8n/`, and root `n8n/`, causing duplicate sources of truth.

## Decision

**Canonical layout** at repo root:

```text
n8n/
  src/          # Router/progress Code nodes (edit here)
  lib/          # Receiver helpers
  workflows/    # PROD workflow JSON + DEV copies under workflows/dev/
  sdk/          # Generated sync/publish SDK files
  settings/
```

Inject script targets `n8n/workflows/cdp_router.json` and
`cdp_progress.json`. `cdp_notifier` is built from
`scripts/build_cdp_notifier_workflow.py`.

## Consequences

- **Phase 1 complete:** Workflow JSON removed from `scrapers/n8n/workflows/` and `muvstok-api/n8n/workflows/`. Only deprecated docs may remain under `scrapers/n8n/docs/`.
- Docs and `.agent/boundaries/n8n.md` list canonical `n8n/` paths only.
- Agents must not treat `scrapers/n8n/shared/dual_dispatch/` as source of truth.
- `make sync-n8n` pushes `cdp_router`, `cdp_scraper`, `cdp_stokapi`,
  `cdp_progress`, and `cdp_notifier` when the optional workflow IDs are
  exported.
- DEV workflow copies are generated under `n8n/workflows/dev/` and synced with
  `make sync-n8n-dev`.
