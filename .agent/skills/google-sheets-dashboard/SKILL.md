---
name: google-sheets-dashboard
description: Audit or improve CDP Google Sheets reporting, dashboards, formulas, pivots, receiver sheet mappings, and xlsx-style exports across Scraper and API Diversos outputs.
---

# Skill: Google Sheets Reporting

Use when changing Sheets formulas, dashboard KPIs, report exports, receiver
sheet mappings, or Telegram/email summaries that rely on sheet-derived metrics.

## Read First

1. `.agent/rules/google-sheets.md`
2. `.agent/knowledge/google-sheets-reporting.md`
3. `docs/n8n/DATA_CONTRACTS.md`
4. Owning service rules when receiver code changes:
   - `scrapers/.agent/rules.md`
   - `muvstok-api/.agent/rules.md`

## Workflow

1. Identify the denominator: unique SKUs, detailed rows, sites, jobs, or offers.
2. Trace the source columns in `Detalhado` before changing formulas.
3. Preserve canonical outcomes:
   `FOUND_PRICE`, `NO_PRICE`, `NOT_FOUND`, `BLOCKED`, `TIMEOUT`, `ERROR`,
   `NOT_QUERIED`.
4. Count found-price success only when `FOUND_PRICE` and
   `has_valid_price=true`.
5. Keep `BLOCKED` and source-health KPIs separate from part availability.
6. Keep seller/location fields as `vendedor`, `uf`, `empresa`, `cnpj`; never
   introduce an `estado` output column.
7. If receiver mappings changed, update the owning service docs/tests and run
   the relevant n8n sync preparation.

## Validation

```bash
python3 scripts/sync_workflow_code_from_shared.py
node -e "const fs=require('fs'); for (const f of ['n8n/workflows/cdp_scraper.json','n8n/workflows/cdp_stokapi.json']) JSON.parse(fs.readFileSync(f,'utf8')); console.log('JSON ok')"
```

If you edit `muvstok-api/scripts/ensure_google_sheets_schema.py`, run its tests
or a dry-run path if available before applying to a real sheet.

## Done When

- KPI formulas document their denominator through sheet layout or nearby labels.
- Found-price, no-price, not-found, blocked, timeout, and error outcomes remain
  visible as distinct categories.
- Service `.agent` memory is updated only if runtime behavior changed.
- No live n8n publish or sheet mutation was run without user approval.
