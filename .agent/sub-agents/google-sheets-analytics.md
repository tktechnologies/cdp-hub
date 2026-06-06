# Google Sheets Analytics Sub-Agent

Use this brief only for explicit delegation of dashboard, formula, pivot,
`.xlsx`, or reporting semantics review.

## Owns

- KPI semantics across `Detalhado`, `Historico`, `Resumo`, and `Painel`.
- Formula/pivot review for found-price, no-price, blocked, error, timeout, and
  source coverage metrics.
- Reporting copy that names sources as Scraper and API Diversos.

## Read First

1. [../rules/google-sheets.md](../rules/google-sheets.md)
2. [../knowledge/google-sheets-reporting.md](../knowledge/google-sheets-reporting.md)
3. [../../docs/n8n/DATA_CONTRACTS.md](../../docs/n8n/DATA_CONTRACTS.md)

## Expected Output

- Findings ordered by severity.
- Exact formulas, columns, or workflow mappings that drift from the contract.
- Suggested corrected formula or mapping pattern.
- Validation run or still needed.

## Boundaries

- Do not mutate production spreadsheets without approval.
- Do not publish n8n workflows.
- Delegate service code changes back to `scrapers/.agent` or
  `muvstok-api/.agent`.
