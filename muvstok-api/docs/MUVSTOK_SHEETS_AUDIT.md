# API Diversos Google Sheets audit

**Updated:** 2026-06-03

Spreadsheet: [cdp_resultados](https://docs.google.com/spreadsheets/d/1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo/edit)

| Tab | gid (reference) |
|-----|-----------------|
| Detalhado | `1831011286` (also `533358674` if sheet was duplicated — use tab name **Detalhado**) |
| Resumo | `79112561` |
| Historico | `1406942676` |

Filter API Diversos rows: `codigo_site = api-diversos` or `origem = API Diversos` on **Historico** (legacy rows may still show `muvstok` until migration).

## Issues fixed (2026-05-26)

| Issue | Cause | Fix |
|-------|--------|-----|
| Resumo **MELHOR PREÇO** empty / N/A | Duplicate helpers shadowed injected block | `strip_shadowed_helpers`; `bestOfferFromListings` |
| **LINK** / **url_produto** | API has no product URL | always **empty** (seller stays in `vendedor`) |
| **Detalhado** wrong columns | Branch in `site` | `site=API Diversos`, `vendedor=filial` |
| Live workflow missing Detalhado/Telegram | SDK sync dropped parallel IF branch | `n8n_workflow_json_to_sdk.mjs` IF fan-out fix |

## Column mapping (Detalhado) — API Diversos

| Sheet column | Source | Notes |
|--------------|--------|--------|
| `job_id` | callback `job_id` | canonical sheet column; legacy `id_job` normalizes here |
| `sku_pesquisado` | requested SKU | uppercase |
| `sku_encontrado` | row `sku` / `skuSemCaractereEspecial` | |
| `correspondencia_exata` | SIM/NAO | |
| `site` | constant `API Diversos` | |
| `preco` | `valorPrecoVenda` | pt-BR; always sale price (no tipo rule) |
| `preco-medio` | `valorCustoMedio` | pt-BR average cost |
| `moeda` | `BRL` | |
| `disponibilidade` | `em_estoque` / `fora_de_estoque` | `qtdeEstoque` (+ aliases) |
| `vendedor` | `nomeFilial` / `apelidoFilial` | |
| `uf` | `uf`, raw `estado`, state name, or location aliases | two-letter Brazilian UF; canonical output column |
| `empresa` | `razaoSocial`, `nomeEmpresa`, company aliases; fallback `nomeFilial` | |
| `cnpj` | `cnpj`, `cnpjFilial`, company/document aliases | normalized 14 digits; blank when unavailable |
| `url_produto` | *(empty)* | API Diversos has no public product URL |
| `origem` | `Brasil` | |
| `titulo_bruto` | `produto` + `[tipo code]` | see stock type codes below |
| `coletado_em` | job `completed_at` | |
| `tempo_busca_ms` | `results[].duration_ms` | |
| `condicao` | `novo` | |
| `duracao_job_s` | `duration_seconds` or timestamp fallback | |
| `marca` | `fabricante` / `montadora` | |
| `codigo_site` | `api-diversos` | filter key |
| `status_resultado` | callback `sku_result` | `FOUND_PRICE`, `NO_PRICE`, `NOT_FOUND`, `BLOCKED`, `TIMEOUT`, `ERROR`, `NOT_QUERIED` |
| `source_health` | callback `source_health` | `WORKING`/`OK`, `BLOCKED`, `TIMEOUT`, `ERROR`, `NOT_QUERIED` |
| `has_valid_price` | normalized price classifier | `TRUE` only when a positive usable sale price exists |

## Result semantics (2026-06-03)

- `status=succeeded` means the worker completed the SKU lookup; it is not a
  found-price result by itself.
- `FOUND_PRICE` + `has_valid_price = TRUE` is the only success signal for
  dashboards, Telegram, and report metrics.
- `NO_PRICE`, `NOT_FOUND`, `BLOCKED`, `TIMEOUT`, `ERROR`, `NOT_QUERIED`, `N/A`,
  and `SEM_DADOS` are never counted as found.
- `BLOCKED` is separate from `NOT_FOUND`. Keep block/access failures visible in
  `source_health` and `status_resultado`.

## Stock type codes in `titulo_bruto`

| Code | Meaning |
|------|---------|
| `0` | NEW |
| `1` | VIVO |
| `2` | DORMENTE |
| `3` | MORTO |
| `4` | ESCRAPE |

API may send numeric codes or names (`Vivo`, `Morto`, …). n8n may append the
normalized `0`–`4` code to `titulo_bruto`, but it does not write separate
`melibox_*` columns to **Detalhado**.

## Column mapping (Resumo)

| Sheet column | Source |
|--------------|--------|
| `CODIGO` | SKU |
| `STATUS` | ✅ / ⚠️ / ❌ from canonical `sku_result` + `has_valid_price` |
| `MELHOR PREÇO` | lowest `valorPrecoVenda` across in-stock rows |
| `SITE` | branch of best offer |
| `LINK` | *(empty)* |
| `DATA` | today pt-BR |

## Pricing rules (2026-05-26)

- **No** `tipoEstoque`-based price selection (removed Vivo→venda / outros→custo).
- **Detalhado:** both `preco` (venda) and `preco-medio` (custo médio) on every row when API returns values.
- **Resumo:** `MELHOR PREÇO` = minimum **sale** price (`valorPrecoVenda`) only.
- Rows need `qtdeEstoque >= 1` for in-stock filter; `rowsForPricing` may include rows with either price when nothing is in stock.
- Price metrics and found counts must filter `has_valid_price = TRUE`.

## Sheet schema migration

Ensure the **Detalhado** header row matches receiver output:
`job_id`, `preco-medio`, `vendedor`, `uf`, `empresa`, `cnpj`, `url_produto`,
`codigo_site`, `status_resultado`, `source_health`, and `has_valid_price`.

The schema helper inserts missing columns structurally so existing data shifts
with its original headers. It normalizes legacy `id_job` to `job_id` and legacy
`estado` to `uf`; if both canonical and legacy headers exist, the legacy header
is renamed with a `_legacy` suffix instead of being deleted. Legacy `melibox_*`
columns are removed because they are not part of the clean reporting schema.

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
uv run --with google-api-python-client --with google-auth \
  python scripts/ensure_google_sheets_schema.py --dry-run
uv run --with google-api-python-client --with google-auth \
  python scripts/ensure_google_sheets_schema.py
```

For the local exported workbook:

```bash
python3 scripts/migrate_cdp_resultados_xlsx.py --dry-run
python3 scripts/migrate_cdp_resultados_xlsx.py
```

Legacy branding (`muvstok` labels):

```bash
python3 scripts/migrate_google_sheets_branding.py --dry-run
python3 scripts/migrate_google_sheets_branding.py
```

## Maintenance

```bash
vim n8n/lib/muvstok_sheet_helpers.js
python3 scripts/patch_muvstok_receiver_workflow.py
python3 scripts/test_muvstok_sheet_helpers.py
cd ../.. && make sync-n8n
```

## Limitations

- Empty `preco` or `preco-medio` when API omits that field (not filled from the other price).
- Branch name remains in `vendedor`; not duplicated in `url_produto` / `LINK`.
