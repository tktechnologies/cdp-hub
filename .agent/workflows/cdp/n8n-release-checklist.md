# CDP n8n release checklist

Platform workflow — run before publishing any n8n change to production.

## Pre-edit

- [ ] User explicitly approved publish
- [ ] Read `.agent/boundaries/n8n.md` and `docs/n8n/LIVE_WORKFLOWS.md`
- [ ] Identified tier: platform router vs scraper receiver vs stokapi receiver

## Router changes (`n8n/src/`)

- [ ] Edited only `n8n/src/*.js`
- [ ] Ran `python3 scripts/sync_workflow_code_from_shared.py`
- [ ] Verified StokAPI uses inline HTTP (no Execute Workflow)
- [ ] `force_refresh: false` unchanged unless intentional
- [ ] SKU pass-through / `CDP_DISPATCH_SAMPLE_SIZE` behavior unchanged unless intentional

## Receiver changes

- [ ] Webhook secret verification intact
- [ ] Callback field mapping matches service schema
- [ ] No secrets in committed JSON

## Push

- [ ] `make sync-n8n` (or documented subset) completed
- [ ] `scripts/n8n_publish.py` reported REST update OK and MCP `publish_workflow` success
- [ ] Updated `.agent/memory/implementation-state.md` and `docs/n8n/LIVE_WORKFLOWS.md` if versions changed

## Post-release smoke

- [ ] `.sku` with 1 test SKU → scraper + stokapi callbacks
- [ ] Sheets receive rows on both pipelines (or documented skip reason)
