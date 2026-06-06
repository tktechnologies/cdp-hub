# Google Sheets Reporting Contract

Root `.agent` owns this cross-service reporting contract because dashboards
combine Scraper and API Diversos rows. Service workspaces own the code that
produces each row.

## Tabs

| Tab | Purpose | Owner |
|-----|---------|-------|
| `SKUs` | Intake rows and processing flags (`CODIGO`, `PROCESSADO`, `ENCONTRADO`) | Router + receivers |
| `Detalhado` | Per-listing or placeholder rows from Scraper and API Diversos | `cdp_scraper`, `cdp_stokapi` |
| `Historico` | Per-job summary rows | Receivers |
| `Resumo` | SKU-level best-price or summary output | Receivers / formulas |
| `Painel` | Dashboard KPIs and charts | Platform reporting |

## Result Fields

| Field | Meaning |
|-------|---------|
| `status_resultado` / `sku_result` | Canonical business result: `FOUND_PRICE`, `NO_PRICE`, `NOT_FOUND`, `BLOCKED`, `TIMEOUT`, `ERROR`, `NOT_QUERIED` |
| `source_health` | Reachability/health: `WORKING` or `OK`, `BLOCKED`, `TIMEOUT`, `ERROR`, `NOT_QUERIED` |
| `has_valid_price` | True only for a positive usable price |

`FOUND_PRICE` plus `has_valid_price=true` is the only found-price success. A
placeholder row records audit evidence but must not increase found counts.

## Seller Columns

`Detalhado` seller/location columns are canonical as:

```text
vendedor
uf
empresa
cnpj
```

Scraper payload fields are `seller_name`, `seller_uf`,
`seller_company_name`, and `seller_cnpj`. API Diversos may receive raw
`estado` aliases from upstream rows, but receivers normalize them to `uf` and
never write `estado`.

## KPI Rules

- **SKUs consultados:** unique requested SKU keys, excluding blanks and
  placeholders such as `SEM_DADOS`.
- **SKUs encontrados:** unique SKU keys with `FOUND_PRICE` and
  `has_valid_price=true`.
- **Linhas Detalhado:** row count; use only for workload/offer volume.
- **Cobertura por site:** per-site unique SKU denominator, not total rows.
- **Blocked rate:** count `source_health=BLOCKED` or `status_resultado=BLOCKED`
  separately from `NOT_FOUND`.
- **Prices:** use positive numeric prices from `FOUND_PRICE` rows only; do not
  average `N/A`, blank, mixed-currency, or no-price rows.

## Where To Edit

| Change | Files |
|--------|-------|
| Scraper row flattening | `scrapers/scripts/patch_scraper_receiver_workflow.py`, `n8n/workflows/cdp_scraper.json` |
| API Diversos row flattening | `muvstok-api/scripts/patch_muvstok_receiver_workflow.py`, `muvstok-api/n8n/lib/`, `n8n/workflows/cdp_stokapi.json` |
| Dashboard schema/formulas | `muvstok-api/scripts/ensure_google_sheets_schema.py` and platform docs |
| Router intake flags | `n8n/src/emparelhar_scraper.js`, receiver workflow mappings |

For scraper-specific result semantics, read
`scrapers/.agent/rules.md`. For API Diversos-specific result semantics, read
`muvstok-api/.agent/rules.md`.
