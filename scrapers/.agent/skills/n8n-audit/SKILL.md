# Skill: Audit CDP n8n Workflows (scraper)

Use when auditing scraper-related n8n: **cdp_router** dispatch arm and **cdp_scraper** receiver.

For router Code edits or syncing all three workflows, use platform skill: `cdp-app/.agent/skills/n8n-router-sync/SKILL.md`.

## Goal

Confirm live n8n, local exports, scraper API contracts, and docs agree.

## Source files

Paths are monorepo-root paths.

| Artifact | Path |
|----------|------|
| Router JSON | `n8n/workflows/cdp_router.json` (Code from `n8n/src/`) |
| Receiver JSON | `n8n/workflows/cdp_scraper.json` |
| Live IDs | `docs/n8n/LIVE_WORKFLOWS.md` |
| API contracts | `scrapers/src/models/schemas.py`, `scrapers/src/api/routes/` |
| Sheets semantics | `docs/n8n/DATA_CONTRACTS.md` |

## Live checks (MCP)

1. `search_workflows` → query `cdp`
2. `get_workflow_details` for `6id6dkinK9xTLfsb` (**cdp_router**) and `VfBSV3WU6on8BXm8` (**cdp_scraper**)
3. Confirm active; receiver webhook: `POST …/webhook/scraper-result`

## Local contract checks

### Router (scraper arm)

1. Posts to `POST /api/v1/jobs` (not `/lookup`) for batch commands
2. Body includes `items`, `sites`, `callback_url`; `force_refresh: false`
3. Default sites: `gm`, `ml`, `vw`, `eu`, `pecadireta`
4. Archived sites not defaulted: `goparts`, `procurapecas`, `ebay`
5. `melibox` explicit/optional only
6. Callback query includes `dual_run=scraper`, `batch_group_id`

### Receiver (cdp_scraper)

1. Verifies `X-Webhook-Secret` from env
2. Preserves statuses: `success`, `not_found`, `no_price`, `blocked`, `timeout`, `error`
3. Google Sheets use `$json.<field>` expressions
4. Detalhado writes `uf`, `empresa`, `cnpj` after `vendedor`; no `estado`
   output column.

## Validation

```bash
node -e "
const fs = require('fs');
for (const f of [
  'n8n/workflows/cdp_router.json',
  'n8n/workflows/cdp_scraper.json',
]) JSON.parse(fs.readFileSync(f,'utf8'));
console.log('JSON ok');
"
```

## Report

Lead with blockers/risks, then verified facts, changes made, and follow-ups. Never include secrets or customer data.
