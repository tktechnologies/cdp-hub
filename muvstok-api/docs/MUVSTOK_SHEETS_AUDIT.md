# API Diversos Google Sheets audit

**Updated:** 2026-05-26

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
| `id_job` | callback `job_id` | |
| `sku_pesquisado` | requested SKU | uppercase |
| `sku_encontrado` | row `sku` / `skuSemCaractereEspecial` | |
| `correspondencia_exata` | SIM/NAO | |
| `site` | constant `API Diversos` | |
| `preco` | `valorPrecoVenda` | pt-BR; always sale price (no tipo rule) |
| `preco-medio` | `valorCustoMedio` | pt-BR average cost |
| `moeda` | `BRL` | |
| `disponibilidade` | `em_estoque` / `fora_de_estoque` | `qtdeEstoque` (+ aliases) |
| `vendedor` | `nomeFilial` / `apelidoFilial` | |
| `url_produto` | *(empty)* | API Diversos has no public product URL |
| `origem` | `Brasil` | |
| `titulo_bruto` | `produto` + `[tipo code]` | see stock type codes below |
| `coletado_em` | job `completed_at` | |
| `tempo_busca_ms` | `results[].duration_ms` | |
| `condicao` | `novo` | |
| `duracao_job_s` | `duration_seconds` or timestamp fallback | |
| `marca` | `fabricante` / `montadora` | |
| `codigo_site` | `api-diversos` | filter key |
| `melibox_tipo` | **stock type code** (0–4) | was text `vivo`/`morto`; see below |
| `melibox_*` (other) | `N/A` | schema parity with scraper tab |

## Stock type codes (`melibox_tipo` / `titulo_bruto`)

| Code | Meaning |
|------|---------|
| `0` | NEW |
| `1` | VIVO |
| `2` | DORMENTE |
| `3` | MORTO |
| `4` | ESCRAPE |

API may send numeric codes or names (`Vivo`, `Morto`, …); n8n normalizes to `0`–`4`.

## Column mapping (Resumo)

| Sheet column | Source |
|--------------|--------|
| `CODIGO` | SKU |
| `STATUS` | ✅ / ⚠️ / ❌ from listings + sale price |
| `MELHOR PREÇO` | lowest `valorPrecoVenda` across in-stock rows |
| `SITE` | branch of best offer |
| `LINK` | *(empty)* |
| `DATA` | today pt-BR |

## Pricing rules (2026-05-26)

- **No** `tipoEstoque`-based price selection (removed Vivo→venda / outros→custo).
- **Detalhado:** both `preco` (venda) and `preco-medio` (custo médio) on every row when API returns values.
- **Resumo:** `MELHOR PREÇO` = minimum **sale** price (`valorPrecoVenda`) only.
- Rows need `qtdeEstoque >= 1` for in-stock filter; `rowsForPricing` may include rows with either price when nothing is in stock.

## Sheet schema migration

Add header `preco-medio` on **Detalhado** (after `preco`):

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
pip install google-api-python-client google-auth
python3 scripts/ensure_google_sheets_schema.py --dry-run
python3 scripts/ensure_google_sheets_schema.py
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
