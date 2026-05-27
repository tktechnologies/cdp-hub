# CDP Sheets + n8n E2E audit — 2026-05-22

Spreadsheet: [cdp_resultados](https://docs.google.com/spreadsheets/d/1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo/edit?gid=79112561#gid=79112561) (tab **Detalhado**, gid `79112561`).

## Test run (CDP scraper API → receiver)

| Item | Value |
|------|--------|
| Job ID | `664e8267-e6cc-4dbf-965d-20c5c25fb9b9` |
| Callback tag | `source=cdp-audit-20260522` |
| SKUs | `631008317R`, `767203M6M01`, `84035768`, `22781768`, `661003M6M00ZZ` |
| Sites | `gm`, `pecadireta`, `melibox` |
| API status | `completed` (~53s) |
| n8n receiver exec | **447** — **success** |

## n8n execution logs

### Starter — `cdp_analise` (exec **445**) — FAIL

Triggered via MCP `execute_workflow` (production). Failed before POST to scraper API.

| Node | Status |
|------|--------|
| Earlier nodes (trigger → DQ path) | success (partial trace) |
| **⚙️ Formatar Payload (Batches)** | **error** |

**Error:** `URLSearchParams is not defined [line 113]` — n8n Code node sandbox does not expose `URLSearchParams`. Blocks manual trigger and scheduled runs until replaced with a manual query-string builder.

**Impact:** Sheet-driven dispatcher did not run in this test. API job was submitted directly (same path worker uses after a successful dispatch).

### Receiver — `cdp_resultado` (exec **447**) — PASS

| Node | Status | Notes |
|------|--------|--------|
| 🔔 Webhook + 🔐 Secret | success | `source=cdp-audit-20260522` |
| 📊 Extrair Dados (Detalhado) | success | **17 rows** |
| 📊 Salvar → Detalhado | success | All 17 appended |
| 📝 Salvar → Histórico | success | 1 job row, `origem=auto` |
| 📋 Salvar → Resumo | success | 5 SKU rows |
| ✅ Marcar ENCONTRADO → CDP_SKUs | success | Updates by `CODIGO` match |

## Detalhado field audit (CDP rows only)

Expected **17** rows for this job — matches n8n output count.

| Check | Result |
|-------|--------|
| `job_id` populated | PASS — UUID on every row |
| `sku_pesquisado` / `sku_encontrado` | PASS |
| `correspondencia_exata` SIM/NAO | PASS |
| `codigo_site` gm / pecadireta / melibox | PASS |
| Placeholder rows (not_found, blocked) | PASS — `preco=N/A`, availability `nao_encontrado` / `bloqueado` |
| `duracao_job_s` | PASS — ~53.19 |
| Resumo `MELHOR PREÇO` vs API `best_price` | PASS — all 5 SKUs match API |
| `marca` | WARN — `N/A` when request `brand` empty; `GM` only for `22781768` |
| `titulo_bruto` | WARN — Peça Direta sometimes `Minha localização` (scraper noise) |

## Separating CDP scraper vs Muvstok in the same spreadsheet

Both projects append to **`1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo`**.

| Signal | CDP scraper (`cdp_resultado`) | Muvstok (`cdp_muvstok-api_receiver`) |
|--------|-------------------------------|----------------------------------------|
| Detalhado job column | **`job_id`** (UUID) | **`id_job`** (e.g. `test-resumo-002`) |
| `codigo_site` | `gm`, `pecadireta`, `melibox`, … | `muvstok` |
| `site` display | Supplier site names | FIAT branch names (e.g. ORLY VALORE FIAT) |
| Historico `origem` | `auto` / `telegram` / `email` | **`muvstok`** |
| SKU examples | Automotive part codes | e.g. `100185638` |

**Filter in Detalhado:** `job_id = 664e8267-e6cc-4dbf-965d-20c5c25fb9b9` OR `codigo_site` in (`gm`,`pecadireta`,`melibox`) — ignore rows with `codigo_site = muvstok` or `id_job` without UUID.

Muvstok exec **449** (same minute) wrote test rows with `id_job` — can confuse column refresh if both headers exist.

## Sheet verification (manual)

1. Open Detalhado tab (gid 79112561).
2. Filter/sort by **`job_id`** = `664e8267-e6cc-4dbf-965d-20c5c25fb9b9` → expect **17** rows.
3. **Historico** — one row, `lista_skus_csv` lists all 5 SKUs, `job_error` lists melibox 403 warnings.
4. **Resumo** — 5 rows; compare `MELHOR PREÇO` to table in audit prompt above.

## Blockers / follow-ups

1. ~~**Fix `cdp_analise`:** replace `URLSearchParams`~~ — **fixed 2026-05-22**, republished `activeVersionId` `00d46df1-e57b-4fa1-a807-a0858b6bbc22`. Also routes **📋 Formatar Confirmação (Planilha)** after **🎲 Limitar SKUs** so Telegram shows 5 SKUs (not full sheet count). Exec **451**: `⚙️ Formatar Payload` **success**; POST failed batch 15/61 with API 500 (separate).
2. **Muvstok Detalhado:** align to `job_id` column name or separate tab — out of CDP scraper scope but affects shared sheet audits.
3. **Muvstok SKUs update:** exec 449 error `Could not find column SKU` — Muvstok workflow expects `SKU` column; CDP sheet uses `CODIGO`.

## Verdict

| Layer | Result |
|-------|--------|
| Scraper API | PASS |
| Receiver → Sheets (CDP) | PASS |
| Starter dispatcher | PASS (URLSearchParams + SKU count routing fixed 2026-05-22) |
| Sheet data contract (CDP job) | PASS with minor scraper noise warnings |
