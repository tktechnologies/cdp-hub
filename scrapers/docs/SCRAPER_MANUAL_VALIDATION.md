# Scraper Manual Validation Runbook

**Last Updated:** 2026-05-12  
**Latest artifacts:** `docs/validation/latest_production_*`

Use this runbook to validate one scraper/SKU at a time with a visible Playwright
browser. It is for live operator checks, not CI. CI should use mocked browser
fixtures and parser tests.

## Required Environment

Set these for local headed validation:

```bash
UV_CACHE_DIR=/tmp/uv-cache
MOCK_SCRAPERS=false
PROXY_ROTATION_ENABLED=false
PLAYWRIGHT_HEADLESS=false
PLAYWRIGHT_SLOW_MO_MS=250
```

All current scrapers use public search flows. Credential variables still exist
for future authenticated flows:

```text
CREDENTIAL_GM_USER, CREDENTIAL_GM_PASS, CREDENTIAL_GM_URL
CREDENTIAL_ML_USER, CREDENTIAL_ML_PASS, CREDENTIAL_ML_URL
CREDENTIAL_VW_USER, CREDENTIAL_VW_PASS, CREDENTIAL_VW_URL
CREDENTIAL_EU_USER, CREDENTIAL_EU_PASS, CREDENTIAL_EU_URL
CREDENTIAL_PROCURAPECAS_USER, CREDENTIAL_PROCURAPECAS_PASS, CREDENTIAL_PROCURAPECAS_URL
CREDENTIAL_PECADIRETA_USER, CREDENTIAL_PECADIRETA_PASS, CREDENTIAL_PECADIRETA_URL
CREDENTIAL_EBAY_USER, CREDENTIAL_EBAY_PASS, CREDENTIAL_EBAY_URL
```

## Manual Command

Run one scraper/SKU:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py \
  --site ml \
  --sku 06K907811B \
  --brand VW \
  --timeout-seconds 120 \
  --slow-mo-ms 250 \
  --hold-seconds 3
```

The runner forces headed mode unless `--headless` is passed, slows browser
actions with `PLAYWRIGHT_SLOW_MO_MS`, and prints a compact summary.

## Output Schema

Each result summary includes:

```json
{
  "site": "ml",
  "sku": "06K907811B",
  "brand": "VW",
  "success": true,
  "price": 298.33,
  "currency": "BRL",
  "status": "success",
  "error_message": "",
  "search_time_ms": 12503,
  "total_results": 8,
  "exact_results": 8,
  "prices": []
}
```

`raw_site_result` in the artifact preserves the full `SiteResult` payload.

## Discovery Demo Command

```bash
UV_CACHE_DIR=/tmp/uv-cache MOCK_SCRAPERS=false PROXY_ROTATION_ENABLED=false \
  uv run --extra dev python scripts/demo_scraper_runs.py --timeout-seconds 75
```

## Status Meanings

| Status | Meaning |
|---|---|
| `success` | At least one exact SKU result has a positive price. |
| `not_found` | No exact product was found. Non-exact candidates may be kept for diagnosis. |
| `no_price` | An exact product was found, but no positive price was available. |
| `blocked` | Anti-bot, CAPTCHA, access-denied, or rate-limit page was detected; do not bypass it. |
| `timeout` | The one-case runner exceeded the configured timeout. |
| `error` | Authentication, browser, selector, or extraction failed unexpectedly. |

## Headed Commands Used On 2026-05-12

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py --site gm --sku 06K907811B --brand VW --timeout-seconds 120 --slow-mo-ms 350 --hold-seconds 5
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py --site ml --sku 06K907811B --brand VW --timeout-seconds 120 --slow-mo-ms 350 --hold-seconds 3
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py --site vw --sku 06K907811B --brand VW --timeout-seconds 120 --slow-mo-ms 350 --hold-seconds 3
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py --site eu --sku 06K907811B --brand VW --timeout-seconds 120 --slow-mo-ms 350 --hold-seconds 3
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py --site pecadireta --sku 06K907811B --brand VW --timeout-seconds 120 --slow-mo-ms 350 --hold-seconds 3
UV_CACHE_DIR=/tmp/uv-cache MELIBOX_SKU_DELAY_MIN=0 MELIBOX_SKU_DELAY_MAX=0 uv run --extra dev python scripts/run_scraper_case.py --site melibox --sku REPLACE_WITH_ACCOUNT_SKU --brand VW --timeout-seconds 120 --slow-mo-ms 350 --hold-seconds 10
```

Additional probes:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py --site vw --sku 04E109119L --brand VW --timeout-seconds 120 --slow-mo-ms 250 --hold-seconds 2
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py --site vw --sku N91194501 --brand VW --timeout-seconds 120 --slow-mo-ms 250 --hold-seconds 2
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py --site vw --sku 03L103483C --brand VW --timeout-seconds 120 --slow-mo-ms 250 --hold-seconds 2
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py --site vw --sku 1S0199262 --brand VW --timeout-seconds 120 --slow-mo-ms 250 --hold-seconds 2
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py --site vw --sku 2GM8547329B9 --brand VW --timeout-seconds 120 --slow-mo-ms 250 --hold-seconds 2
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py --site vw --sku 5GB8059159B9 --brand VW --timeout-seconds 120 --slow-mo-ms 250 --hold-seconds 2
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py --site gm --sku 84250224 --brand GM --timeout-seconds 120 --slow-mo-ms 250 --hold-seconds 2
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/run_scraper_case.py --site gm --sku 94700547 --brand GM --timeout-seconds 120 --slow-mo-ms 250 --hold-seconds 2
```

## Latest Headed Summary

| Scraper | URL | SKU | Success | Price | Status |
|---|---|---:|---:|---:|---|
| GM / Chevrolet | `https://www.pecachevrolet.com.br` | `94700547` | false |  | `not_found` |
| Mercado Livre | `https://lista.mercadolivre.com.br` | `06K907811B` | true | BRL 298.33 | `success` |
| Volkswagen | `https://pecas.vw.com.br` | `06K907811B` | false |  | `not_found` |
| FastParts Export | `https://export.fastparts.is` | `06K907811B` | true | USD 292.13 | `success` |
| Procura Pecas | *(archived 2026-05-13)* | — | — | — | not active |
| PecaDireta | `https://www.pecadireta.com.br` | `06K907811B` | false |  | `no_price` |
| eBay | *(archived 2026-05-13)* | — | — | — | not active |
| Melibox | `https://app.melibox.com.br` | account SKU required | pending |  | pending credentials |

Minimum future smoke SKU from the current evidence: `06K907811B`. It validates
`success`, `not_found`, and `no_price` across the enabled scraper set. It does
not provide a priced positive on the official VW store; all seven provided VW
SKUs returned `not_found` there on 2026-05-12.

## Per-Scraper Notes

| Site | Strategy / Selectors | SKU Examples | Known Edge Cases | Troubleshooting |
|---|---|---|---|---|
| `gm` | Public VTEX search `/busca?q={sku}`. Sets CEP through visible `input.input-CEP` and `button` text `Localizar`; cards use VTEX product-summary/product-card selectors. | `84250224`, `94700547`, `06K907811B` for negative VW check. | Stored browser state may preserve default CEP `01001-000`; clear or overwrite with `80220001`. Search can render no cards even after CEP is set. | Watch CEP modal first. If prices do not render, inspect `.header-items-right-cep`, visible CEP input, and localStorage `CEP`. |
| `ml` | Public search `/{sku}_NoIndex_True`; cards from `li.ui-search-layout__item`, `div.ui-search-result`, and poly-card layouts. | `06K907811B`. | Condition is often not exposed in card text, so new/used can be `unknown`; exact SKU in title is the acceptance gate. | Check for CAPTCHA/access-denied text and selector drift in title/price classes. |
| `vw` | Official VTEX/SPA search `/busca?q={sku}`; JS evaluates product/card/gallery selectors with BRL price regex. | Provided VW list: `06K907811B`, `04E109119L`, `N91194501`, `03L103483C`, `1S0199262`, `2GM8547329B9`, `5GB8059159B9`. | All provided SKUs returned `not_found` on 2026-05-12. A manually verified VW positive SKU is still needed. | In headed mode, confirm whether cards appear visually. If cards appear but extraction is empty, update the JS card selector list. |
| `eu` | Angular SPA at `export.fastparts.is`; fills `input[placeholder*='part code']`, presses Enter, extracts table rows. | `06K907811B`, Mercedes examples with leading `A` for normalization checks. | Duplicate rows can appear; delivery/availability extraction is currently coarse. Currency must remain USD/EUR. | If input is missing, inspect placeholder text and Angular render timing. |
| `procurapecas` | **Archived** (2026-05-13). Code in `src/scrapers/procurapecas.py` for reference only. | — | — | — |
| `pecadireta` | SPA search; listing cards; opens `/produto/` when card has exact SKU but no price; `itemprop` / body `R$` on detail. | `06K907811B`, `5U6867287Y20`. | Out-of-stock can still yield price after detail visit. | Inspect product URL path and title when `sku_found` is empty. |
| `ebay` | **Archived** (2026-05-13). Code in `src/scrapers/ebay.py` for reference only. | — | — | — |
| `melibox` | Authenticated Sellerbox app; **advProductPosition** screen with **Frase/Palavra** + **Enviar**, then table row extraction. | Requires a real account SKU. | Missing credentials fail authentication; if Melibox changes ids/labels, update phrase/Enviar selectors in `melibox.py`. Per-SKU context rotation is available when proxy rotation is enabled. | Run headed with `MELIBOX_SKU_DELAY_MIN=0` / `MAX=0`, capture selectors only, and never commit browser state or screenshots. |
