# Google Sheets Reporting Rules

**Applies to:** Google Sheets dashboards, formulas, pivots, `.xlsx` exports,
Telegram/email summaries that read sheet data, and n8n receiver mappings into
`Detalhado`, `Historico`, `Resumo`, or `Painel`.

## Canonical Metrics

- Found-price success means `status_resultado` or `sku_result` is
  `FOUND_PRICE` **and** `has_valid_price` is true.
- Never count row existence in `Detalhado` as success.
- Keep `NO_PRICE`, `NOT_FOUND`, `BLOCKED`, `TIMEOUT`, `ERROR`, and
  `NOT_QUERIED` as separate outcomes.
- Captcha, anti-bot, 403, access-denied, and protected-source pages are
  `BLOCKED`, not `NOT_FOUND`.
- Count SKU metrics with unique SKU keys; count offer/listing metrics with row
  counts. Do not mix those denominators in one KPI.

## Detalhado Columns

- Seller metadata columns are `vendedor`, `uf`, `empresa`, `cnpj`.
- Do not add or write an `estado` column. Raw `estado` or state-name aliases
  normalize to two-letter `uf`.
- Receivers must write `status_resultado`, `source_health`, and
  `has_valid_price` for every result or placeholder row.

## Source Names

- User-facing stock source name: **API Diversos**.
- Technical names allowed only for routes, env vars, workflow paths, and
  historical compatibility: `StokAPI`, `muvstok-result`,
  `/api/v1/muvstok/*`.

## SKUs robot columns (PROCESSADO / ENCONTRADO / NOTIFICADO)

- Updates must use `row_number` from a Google Sheets read in the same branch.
- Remap Code nodes spread the read row and keep `pairedItem`; never emit only
  `{ row_number, STATUS }` into an Update Row node.

## Validation

- Inspect formulas for `FOUND_PRICE` and `has_valid_price`; formulas that only
  check non-empty rows or prices are suspect.
- Verify pivots separate status distribution from price-found coverage.
- When receiver mappings change, run the owning service contract checks and the
  n8n JSON parse check before publish.

Detailed field map: [../knowledge/google-sheets-reporting.md](../knowledge/google-sheets-reporting.md).
