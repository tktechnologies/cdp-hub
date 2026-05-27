# n8n Release

See also: [.agent/workflows/cdp/n8n-release-checklist.md](../../.agent/workflows/cdp/n8n-release-checklist.md).

## Checklist

1. Edit `n8n/src/*.js` (not JSON inline code).
2. `python3 scripts/sync_workflow_code_from_shared.py`
3. Review `n8n/workflows/cdp_router.json` diff.
4. Run scraper tests: `make -C scrapers test lint`
5. **User approval** required before publish.
6. `make sync-n8n`
7. Update `.agent/memory/implementation-state.md` if workflow IDs or behavior changed.

## Webhooks (stable)

- `scraper-result` → `cdp_scraper`
- `muvstok-result` → `cdp_stokapi`
