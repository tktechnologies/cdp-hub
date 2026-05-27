# Scraper Field Guide

**Last Updated:** 2026-05-21  
**Latest Production Artifacts:** `docs/validation/latest_production_*`  
**Production Curl Smoke:** `docs/validation/latest_production_curl_smoke.json`

This guide is the operator and agent map for the live webscrapers. Think of each
scraper as a small field instrument: it has a source story, a search ritual, a
data contract, and a few ways it can lie to us when the site changes.

## Production Curl Snapshot - 2026-05-14

The production Container App smoke suite was run through `/api/v1/lookup`
against image `cdpscraperprodacr.azurecr.io/cdp-scraper:melibox-blocked-20260514-0135`.

| Site | SKU | Result | What We Learned |
|---|---:|---|---|
| `gm` | `22781768` | `success`, 3 BRL prices | Dealer-row extraction works in production; best price came from the lowest exact BRL offer. |
| `ml` | `06K907811B` | `not_found` | This previously positive SKU no longer returns an exact priced production result; refresh the smoke SKU or selectors. |
| `vw` | `5U6867287Y20` | `success`, BRL price | API -> Celery -> worker -> Playwright -> PostgreSQL path is healthy for VW. |
| `eu` | `06K907811B` | `success`, 2 USD rows | FastParts production search returns duplicate exact VAG rows; consider de-duplication. |
| `pecadireta` | `06K907811B` | `success`, BRL price | Exact product page returns a price, but `raw_title` is weak (`Minha localização`) and needs parser refinement. |
| `melibox` | `51766536` | `blocked` | Key Vault secrets are present/non-empty and Container Apps expose them, but the worker receives `403 forbidden` at the Melibox login entry before credentials can be used. |

Infrastructure notes from the same audit:
- API and N8N health endpoints returned `200`.
- Azure PostgreSQL persistence was verified after curl jobs.
- Worker logs no longer show the asyncpg pooling crash after the 2026-05-14 fix.
- Worker logs still warn that proxy rotation is enabled with no configured
  proxy URLs.
- Melibox now drops stale browser state and retries the login entry once, but
  the production worker still receives `403 forbidden`; resolve access/proxying
  before expecting SKU `51766536` to succeed in Azure.

## Demo Snapshot - 2026-05-12

Local Docker Postgres/Redis were started with `docker compose up -d postgres redis`.
The demo runner executed each scraper directly with real Playwright browsers:

```bash
UV_CACHE_DIR=/tmp/uv-cache MOCK_SCRAPERS=false PROXY_ROTATION_ENABLED=false \
  uv run --extra dev python scripts/demo_scraper_runs.py \
  --output docs/validation/latest_scraper_demo_results.json \
  --timeout-seconds 75
```

| Site | SKU | Result | What We Learned |
|---|---:|---|---|
| `gm` | `84250224` | `error` | Public portal loaded, but CEP modal fill failed because Playwright found a hidden `input-CEP`. |
| `ml` | `84250224` | `success`, 8 listings | Mercado Livre returns priced cards, but the current exact-match logic is too permissive: all returned parts were `exact_match=false`. |
| `vw` | `5C0941005K` | `not_found` | Site loaded and extraction completed; this demo SKU did not produce cards. |
| `eu` | `A0001234567` | `not_found` | Mercedes normalization worked (`A000...` -> `000...`); no matching rows for the demo SKU. |
| `procurapecas` | `84250224` | `not_found` | VTEX page loaded and JS extraction completed; demo SKU had no product card. |
| `pecadireta` | `84250224` | `not_found` | SPA loaded and no-results detection fired. |
| `ebay` | `84250224` | `not_found` | eBay returned an Access Denied page; scraper currently maps this to zero results instead of an error. |
| `melibox` | `84250224` | pending | Authenticated Sellerbox source added on 2026-05-13; live validation needs credentials and a known account listing SKU. |

## Headed Validation Snapshot - 2026-05-12

Use `scripts/run_scraper_case.py` for one visible browser run per scraper/SKU.
The latest runbook and commands are in `docs/SCRAPER_MANUAL_VALIDATION.md`.

| Site | SKU | Result | What We Learned |
|---|---:|---|---|
| `gm` | `94700547` | `not_found` | CEP modal submission now uses the visible input and `Localizar`; the sample SKU did not produce cards. |
| `ml` | `06K907811B` | `success`, BRL price | Exact SKU cards were returned with prices. |
| `vw` | `06K907811B` | `not_found` | The official VW store produced no cards; all seven provided VW SKUs were also `not_found`. |
| `eu` | `06K907811B` | `success`, USD price | FastParts returned exact VAG rows. |
| `goparts` | `06K907811B` | `not_found` | Headed run completed without the earlier timeout. |
| `procurapecas` | `06K907811B` | `not_found` | VTEX search completed, no exact product cards. |
| `pecadireta` | `06K907811B` | `no_price` | Exact product page exists, but no positive price was visible. |
| `ebay` | `06K907811B` | `success`, BRL price | eBay BRL prices with dot decimal separators now parse correctly. |

## Targeted Browser Fix Snapshot - 2026-05-13

The root `demo` runner was rerun after DOM fixes:

| Site | SKU | Result | What We Learned |
|---|---:|---|---|
| `gm` | `22781768` | `success`, 3 dealer prices | Current DOM exposes dealer rows via `.tab-precos-row-2024`; prices came from `.concessionaria-preco-2024-value`. |
| `pecadireta` | `5U6867287Y20` | `no_price` | Exact product exists at `/produto/volkswagen/5u6867287y20?obsoleto=0`, but page says temporarily out of stock and exposes no price. |
| `vw` | `5U6867287Y20` | `success`, BRL price | Exact SKU evidence appears in title and URL; scraper now marks it exact. |

All-scraper SKU probe positives:

| Site | SKU | Result |
|---|---:|---|
| `ml` | `06K907811B` | `success`, BRL price |
| `vw` | `5U6867287Y20` | `success`, BRL price |
| `vw` | `06K907811B` | `success`, BRL price |
| `eu` | `06K907811B` | `success`, USD price |

Remaining blockers from the same probe: repeated live requests produced explicit
`blocked` statuses for `procurapecas` and `ebay`. `goparts` was archived on
2026-05-13 after repeated direct `/busca/{sku}` browser timeouts.

## Shared Contract

Every scraper must return `SiteResult` containing `PartResult` records with:

- `sku_searched`, `sku_found`, and `exact_match`
- `site`, `site_name`, `price`, `currency`
- `condition`, `availability`, `origin`
- `seller_name`, `product_url`, `raw_title`, `scraped_at`

Exact SKU matching is the spine of the system. If a marketplace gives a nice
price but the title does not contain the exact normalized SKU, keep it visible
for diagnosis but do not let it become `best_price`. Shared site statuses are
`success`, `not_found`, `no_price`, `blocked`, `timeout`, and `error`.

## Shared Anti-Bot Layers - 2026-05-19

All active Playwright scrapers inherit the shared anti-bot baseline from
`BaseScraper`:

- Browser context profile: locale `pt-BR`, timezone `America/Sao_Paulo`,
  desktop viewport, Chromium-compatible user-agent, and supplemental
  `Accept-Language` header. Chromium keeps document-only headers on document
  navigations; do not force them on every request. Configure
  `BROWSER_USER_AGENTS` as a JSON list when
  a source needs user-agent rotation; leave it empty to derive a matching
  Chromium UA from the installed Playwright browser.
- Session continuity: storage state remains per site under `browser_states/`.
  Do not commit these files.
- Pacing: inter-SKU delays come from `SCRAPE_DELAY_MIN` /
  `SCRAPE_DELAY_MAX`; in-page interaction jitter comes from
  `SCRAPER_ACTION_DELAY_*`; source-specific delays such as Melibox still apply.
- Block handling: main-document `403` / `429`, visible CAPTCHA/challenge pages,
  Cloudflare/Turnstile text, and access-denied pages are retried with
  `ANTI_BOT_RETRY_ATTEMPTS` plus exponential jitter, then reported as
  `blocked` if still restricted.
- Proxy layer: `PROXY_ROTATION_ENABLED` and `PROXY_URLS` assign one proxy per
  browser context. Authenticated sources should rotate only between contexts,
  never halfway through a login/search flow.

This baseline prevents avoidable bot signals; it is not challenge bypass logic.
If a site says no after the bounded retry/backoff, keep the result honest as
`blocked`.

`scripts/demo_scraper_runs.py` uses configurable delays for headless/headed
validation. Use `--timeout-seconds` to adjust per-source time budget.

## GM - Peça Chevrolet

Story: GM is the official-looking public Peça Chevrolet portal. It behaves like
a normal VTEX store until pricing depends on a dealership/CEP session. The
scraper's first job is not login in the usual sense; it is setting location.

Search path: `https://www.pecachevrolet.com.br/busca?q={SKU}`

Current behavior:
- Uses `BaseScraper.initialize()`, so proxy rotation and `PLAYWRIGHT_HEADLESS`
  apply.
- Sets CEP `80220001` before searching.
- Returns BRL, `new`, origin `Brasil`.

Latest blocker:
- Current price DOM is dealer-row based. Use `.tab-precos-row-2024` for offers,
  `.concessionaria-name-2024` / `.concessionaria-cidade-2024` for dealer info,
  and `.concessionaria-preco-2024-value` for price.

Agent moves:
- Inspect the modal DOM and choose the visible CEP input, not the first matching
  input.
- Add a focused test around the CEP selector fallback.
- If headless remains blocked, document `PLAYWRIGHT_HEADLESS=false` as a manual
  validation mode instead of forcing it in code.

## Mercado Livre

Story: Mercado Livre is noisy but useful. It gives many priced cards quickly,
and that is exactly why strict matching matters: search can drift into nearby
products and even unrelated catalog cards.

Search path: `https://lista.mercadolivre.com.br/{SKU}_NoIndex_True`

Current behavior:
- Public search, no login.
- Filters out used items when condition is detected.
- Parses BRL prices from listing cards.
- Uses card title/text/URL evidence first, then opens ambiguous candidates and
  confirms the SKU on the product detail page when cards do not expose it.

Latest demo:
- `51766536` returned 5 detail-confirmed exact BRL-priced listings; best live
  demo price was `R$ 779,90` on 2026-05-19.

Agent moves:
- Keep the detail-page pass bounded; ML is useful but slower when the SKU only
  appears in product attributes like `Número de peça`.
- Do not mark a card exact just because it came from the SKU search page. Keep
  explicit SKU evidence in title, card text, URL, or detail page body.

## VW Official

Story: VW is a calmer public store. It is SPA/VTEX-like and usually responds
without heavy anti-bot drama. The challenge is picking SKUs that actually exist
and catching rendered product cards reliably.

Search path: `https://pecas.vw.com.br/busca?q={SKU}`

Current behavior:
- Public search, no login.
- VW-specific normalization removes separators.
- Parses BRL prices from client-rendered cards.

Latest demo:
- `5C0941005K` loaded cleanly but returned no product cards.

Agent moves:
- Build a small real VW SKU manifest from manual browser evidence.
- Save card HTML snippets for parser tests once a known positive SKU is found.
- Keep condition `new` unless site starts exposing used/remanufactured states.

## EU Imports - FastParts Export

Story: EU Imports is the foreign-currency source. It is an Angular table, not a
marketplace card wall. The Mercedes rule matters here: remove the first
character before searching European sources.

Search path: `https://export.fastparts.is`, fill `input[placeholder*='part code']`

Current behavior:
- Public SPA interaction.
- Mercedes normalization: `A0001234567` -> `0001234567`.
- Parses EUR/USD and keeps source currency.

Latest demo:
- Normalization worked; demo SKU returned no rows.

Agent moves:
- Never compare EU prices against BRL in `best_price` without conversion.
- Capture a positive Mercedes/VAG row and add parser fixtures.
- Watch for changed placeholder text; Angular apps often shift labels.

## GoParts - Archived

Story: GoParts was the stubborn one. It is valuable because it covers many
brands, but the page repeatedly hung under Playwright due to Cloudflare and
analytics.

Search path: `https://goparts.com.br/busca/{SKU}`

Current behavior:
- Code remains in `src/scrapers/goparts.py` for reference.
- It is removed from `SCRAPER_REGISTRY`, API defaults, and local validation
  requirements. Local demo scripts can still run it explicitly with the
  2026-05-19 demo SKU map.

Latest demo:
- `7091011` is blocked from the current headless demo network by Cloudflare
  (`cf-mitigated: challenge`). The scraper now detects this before browser
  navigation so the demo reports `blocked` in seconds instead of timing out.

Agent moves:
- Do not spend more production time on GoParts browser scraping unless the user
  explicitly reopens it.
- If GoParts returns later, prefer an official/API-backed integration over the
  browser flow.

## Procura Peças

Story: Procura Peças is a VTEX-style store, not a multi-seller marketplace. It
is useful when titles contain `REF` codes because that gives us clean SKU
evidence.

Search path: `https://procurapecas.com.br/{SKU}?map=ft`

Current behavior:
- Public search, no login.
- Extracts product cards via JS.
- Prefers PIX price when present.
- Seller is normalized to `Procura Peças`.

Latest demo:
- `51766536` is blocked from the current demo network by Cloudflare managed
  challenge, including the public VTEX product-search API endpoint.

Agent moves:
- Use `blocked` for Cloudflare/CAPTCHA pages; do not turn this into a parser
  failure.
- Find and store positive `REF:.{SKU}` examples from an allowed browser/network.
- Test PIX/list-price selection with static HTML snippets.
- Keep `condition=new` for this store unless site copy says otherwise.

## Peça Direta

Story: Peça Direta is a marketplace. It can have useful supplier diversity, but
condition and seller extraction need more care than single-store sources.

Search path: `https://www.pecadireta.com.br/procurar/pecas?query={SKU}`

Current behavior:
- Public SPA search.
- Parses cards/links with BRL prices.
- Maps text hints to `new`, `used`, or `unknown`.

Latest demo:
- `5U6867287Y20` and `06K907811B` produce exact product cards, but both were
  temporarily out of stock on 2026-05-13 and should return `no_price`, not
  `not_found`.

Agent moves:
- Build fixtures from known positive marketplace cards.
- Preserve seller/location when present; they matter for operations.
- Do not default unknown condition to new.
- Only follow same-site `/produto/` links. Never treat pagination, social,
  WhatsApp, or footer links as product pages.

## eBay

Story: eBay is the international marketplace source. It is broad and volatile:
the DOM changes often and access-denied pages can look like successful empty
searches unless explicitly detected.

Search path: `https://www.ebay.com/sch/i.html?_nkw={SKU}&_sacat=6028`

Current behavior:
- Public search in auto parts category.
- Parses USD/BRL/EUR.
- Maps condition from listing text.
- Uses an eBay-specific block detector so hidden challenge markup does not
  discard visible search results.

Latest demo:
- `5473368` returned 18 exact priced rows on 2026-05-19; best live demo price
  was `R$ 1.372,47`.

Agent moves:
- Keep visible challenge/interstitial detection, but do not treat hidden
  CAPTCHA markup as a block when result rows are visible.
- Add proxy/session rotation before treating eBay production data as reliable.
- Capture static examples for standard `.s-item` and fallback layouts.

## Melibox - Sellerbox

Story: Melibox is an authenticated Sellerbox portal for Mercado Livre sellers.
Unlike public ML search, it can only show account-managed listings, products, or
stock rows. Treat it as a private inventory/listing source, not as a public web
marketplace.

Search path: login at `https://app.melibox.com.br`, then open
`/advProductPosition` (or the full `CREDENTIAL_MELIBOX_URL` when it already
targets that route), enter the SKU in **Frase/Palavra**, click **Enviar**, and
parse table rows that contain the SKU text.

Current behavior:
- Uses configured `CREDENTIAL_MELIBOX_USER`, `CREDENTIAL_MELIBOX_PASS`, and
  `CREDENTIAL_MELIBOX_URL`.
- Uses the live **Frase/Palavra** input selector `#textoPesquisa` on
  `/advProductPosition`, submits **Enviar**, and reads prices from the table
  `R$` column even when the cell omits the currency prefix.
- Adds source-specific per-SKU pacing through `MELIBOX_SKU_DELAY_MIN` and
  `MELIBOX_SKU_DELAY_MAX`.
- When proxy rotation is enabled, can rotate the browser context between SKUs
  through `MELIBOX_ROTATE_CONTEXT_PER_SKU=true`.
- Only exact SKU evidence in row/card text, title, or URL can produce success.

Latest evidence:
- Live authenticated run on 2026-05-13 for SKU `51766536` returned `success`
  with 17 exact rows and BRL prices.
- Production smoke on 2026-05-14 for SKU `51766536` returned `blocked` with
  `Melibox login entry returned 403/access block` on image
  `cdpscraperprodacr.azurecr.io/cdp-scraper:melibox-blocked-20260514-0135`.
- Local smoke without credentials returns `Authentication failed`.

Agent moves:
- Do not commit browser state, screenshots, cookies, or account data.
- If **advProductPosition** / **Frase/Palavra** / **Enviar** selectors drift,
  update `docs/scrapers/melibox.md` and add parser/helper tests in the same turn.
- Return `blocked` for access controls; do not add CAPTCHA or challenge bypasses.

## Agent Checklist

Before changing a scraper:
- Read `src/scrapers/base.py` and the target scraper file.
- Use exact SKU matching as the acceptance gate.
- Prefer parser fixtures over live-site tests for unit coverage.

When running live validation:
- Use `scripts/demo_scraper_runs.py` for local discovery.
- Use `scripts/validate_local_scrapers.py` with a curated manifest.
- Use `scripts/production_scraper_curl_smoke.py` for production.
- Keep screenshots, cookies, browser state, and customer SKU manifests out of git.
