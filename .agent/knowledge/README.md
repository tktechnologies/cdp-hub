# Platform Knowledge Index

This folder is the root `.agent` control-plane knowledge layer. It should help
agents understand how CDP fits together without copying service internals.

## What Belongs Here

- Cross-service maps and ownership models.
- How root `.agent` stays aligned with service `.agent` workspaces.
- Durable conventions that apply to n8n, API Diversos, and Scraper together.

## What Does Not Belong Here

- Full service implementation notes. Put those in `scrapers/.agent/` or
  `muvstok-api/.agent/`.
- Live deployment facts. Put those in `.agent/memory/implementation-state.md`
  or the owning service memory.
- Reusable workflows. Put those in `skills/`, `commands/`, or `workflows/`.

## Files

| File | Purpose |
|------|---------|
| [service-catalog.md](service-catalog.md) | Cross-service ownership, entries, contracts, and gates |
| [workspace-sync.md](workspace-sync.md) | What to update in root vs service `.agent` workspaces |
| [google-sheets-reporting.md](google-sheets-reporting.md) | Sheets tabs, KPI definitions, formulas, pivots, dashboard UX |
