# audit-google-sheets

**Purpose:** Review Google Sheets reporting for semantic drift before changing
dashboards, formulas, receiver mappings, or exports.

## Read

1. [../rules/google-sheets.md](../rules/google-sheets.md)
2. [../knowledge/google-sheets-reporting.md](../knowledge/google-sheets-reporting.md)
3. [../../docs/n8n/DATA_CONTRACTS.md](../../docs/n8n/DATA_CONTRACTS.md)

## Local Checks

```bash
rg -n "FOUND_PRICE|has_valid_price|status_resultado|source_health|estado|uf|empresa|cnpj" \
  n8n scrapers/scripts muvstok-api/scripts docs .agent
```

For workflow JSON sanity:

```bash
node -e "const fs=require('fs'); for (const f of ['n8n/workflows/cdp_scraper.json','n8n/workflows/cdp_stokapi.json']) JSON.parse(fs.readFileSync(f,'utf8')); console.log('JSON ok')"
```

## Audit Points

- Found-price formulas require `FOUND_PRICE` and `has_valid_price=true`.
- `NO_PRICE`, `NOT_FOUND`, `BLOCKED`, `TIMEOUT`, `ERROR`, and `NOT_QUERIED`
  are not collapsed into one bucket.
- `BLOCKED` is tracked as source health, not inventory absence.
- `Detalhado` uses `vendedor`, `uf`, `empresa`, `cnpj`; no output
  `estado` column.
- SKU KPIs use unique SKUs; offer/listing KPIs use row counts.
- SKUs tab robot columns: Update Row nodes must receive items with `pairedItem`
  from a prior read; grep remap nodes for `pairedItem` and `...row` spread.

## Safety

Do not mutate production spreadsheets, publish n8n workflows, or deploy receiver
patches without explicit user approval.
