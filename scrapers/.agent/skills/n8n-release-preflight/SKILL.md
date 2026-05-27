# Skill: CDP n8n Release Preflight

Run before publishing or updating live n8n workflows through MCP.

## Checklist

1. **JSON parses:** All files in monorepo `n8n/workflows/` and `n8n/settings/` parse cleanly.
2. **Code nodes:** Every Code node parses as valid JavaScript.
3. **Live state:** MCP confirms `cdp_router`, `cdp_scraper`, and `cdp_stokapi` active (see [docs/n8n/LIVE_WORKFLOWS.md](../../../../docs/n8n/LIVE_WORKFLOWS.md)).
4. **Dispatcher checks (`cdp_router`):**
   - Posts to `POST /api/v1/jobs` (scraper) and `POST /api/v1/muvstok/jobs` (StokAPI) inline — no Execute Workflow for StokAPI
   - `X-API-Key` from env (not hardcoded)
   - Scraper body: `items`, `sites`, `callback_url`, `priority`, `force_refresh: false`
   - Default sites: `gm`, `ml`, `vw`, `eu`, `pecadireta`
   - No archived sites defaulted
5. **Receiver checks:**
   - Scraper webhook path: `scraper-result`
   - StokAPI webhook path: `muvstok-result`
   - Secret from env (`CDP_CALLBACK_WEBHOOK_SECRET` / fallbacks)
   - All statuses preserved distinctly
   - Google Sheets mappings use `$json.<field>`
6. **Environment:** Required vars present on n8n container.
7. **Docs updated:** [docs/n8n/LIVE_WORKFLOWS.md](../../../../docs/n8n/LIVE_WORKFLOWS.md) if IDs or behavior changed.
8. **Git clean:** `git diff --check` passes.

## Blockers (do not publish if any)

- Live differs materially from export with no resolution plan.
- API key or webhook secret hardcoded in repo.
- Dispatcher sends archived sites by default.
- Receiver cannot distinguish all site statuses.
- Publish would break credential bindings without reconnect plan.
- Real customer data in logs, docs, or commits.

## Post-Publish

After MCP `update_workflow` + `publish_workflow`:
1. `get_workflow_details` to verify graph.
2. Check credential bindings (HTTP, Sheets, Telegram).
3. Run one smoke job and check receiver execution.
