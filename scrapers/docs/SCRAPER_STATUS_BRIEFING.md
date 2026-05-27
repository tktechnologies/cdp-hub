# CDP Scrapers - Full Status Briefing

**Date:** 2026-05-21  
**Prepared for:** Team meeting

---

## Production Infrastructure

- **Image:** `callback-strip-20260521-1649` (API + Worker)
- **Host:** Azure Container Apps (East US 2)
- **Stack:** FastAPI + Celery/Redis + PostgreSQL + Playwright
- **Scrape Cache:** Redis 24h per-site SKU cache, validated (5/5 SKU audits)
- **FQDN:** `cdp-scrapers-api-prod.bravecoast-b14d791e.eastus2.azurecontainerapps.io`
- **n8n:** `https://automacao.tktechnologies.com.br`

---

## Active Scrapers (6 registered, 4 fully working)

| # | Scraper | Site | Status | Auth | Currency | Last Evidence |
|---|---------|------|--------|------|----------|---------------|
| 1 | **GM** | pecachevrolet.com.br | **WORKING** | Public (CEP-based) | BRL | 3 dealer prices returned |
| 2 | **VW** | pecas.vw.com.br | **WORKING** | Public (CEP-based) | BRL | Exact SKU match with price |
| 3 | **EU Imports** | export.fastparts.is | **WORKING** | Public (Angular SPA) | USD/EUR | 2 exact VAG rows |
| 4 | **Peca Direta** | pecadireta.com.br | **WORKING** | Public (marketplace) | BRL | Exact product with price |
| 5 | **Mercado Livre** | lista.mercadolivre.com.br | **DEGRADED** | Public | BRL | Smoke SKU stale/not returning |
| 6 | **Melibox** | app.melibox.com.br | **BLOCKED (403)** | Credentials required | BRL | Login entry returns 403 Forbidden |

---

## How Each Active Scraper Works

### 1. GM (Peca Chevrolet)

Public VTEX portal. Sets CEP `80220001` to unlock dealer pricing, searches
`/pesquisa/?numeropeca={SKU}`, clicks into product detail pages, extracts
multiple dealer/shop prices from `.tab-precos-row-2024` rows. Returns BRL,
condition `new`, origin Brasil.

### 2. VW Official

Public VTEX/SPA store. Sets CEP, navigates to `/todas-categorias?q={SKU}`,
waits for client-rendered product cards, extracts prices (prefers PIX price
when available). Returns BRL, condition `new`.

### 3. EU Imports (FastParts)

Public Angular SPA. Navigates to `export.fastparts.is`, fills
`input[placeholder*='part code']`, presses Enter, parses PrimeNG table rows.
Mercedes normalization removes first character (e.g., `A0001234567` ->
`0001234567`). Returns USD/EUR from European warehouses.

### 4. Peca Direta

Public marketplace SPA. Navigates to `/procurar/pecas?query={SKU}`, extracts
listing cards or clicks into `/produto/` detail pages, supports multiple
sellers/prices per SKU. Returns BRL, maps condition from page text.

### 5. Mercado Livre

Public marketplace. Navigates to `/{SKU}_NoIndex_True`, extracts listing cards,
filters used items out, validates SKU evidence in title/card/URL/detail page.
When card-level evidence is ambiguous, opens up to 6 detail pages to confirm
exact match. Returns BRL.

### 6. Melibox (Sellerbox)

**Authenticated** portal for ML sellers. Logs in with credentials, navigates to
`/advProductPosition`, enters SKU in "Frase/Palavra" field (`#textoPesquisa`),
clicks "Enviar", parses table rows. Has per-SKU pacing and optional context
rotation. Returns BRL.

---

## Archived Scrapers (3 - removed from registry)

| # | Scraper | Site | Why Archived | Archived Date |
|---|---------|------|-------------|---------------|
| 7 | **GoParts** | goparts.com.br | Cloudflare challenge blocks headless browsers; repeated browser timeouts | 2026-05-13 |
| 8 | **Procura Pecas** | procurapecas.com.br | Cloudflare managed challenge blocks both browser and VTEX API endpoints | 2026-05-13 |
| 9 | **eBay** | ebay.com | Access Denied / "Pardon Our Interruption" interstitial from eBay anti-bot | 2026-05-13 |

### How Each Archived Scraper Was Working

**7. GoParts** — Public parts aggregator. Navigated to `/busca/{SKU}`, blocked
analytics scripts (Hotjar, Facebook Pixel, GA) to prevent hangs, extracted
cards/tables via JS. Had a pre-flight Cloudflare check via `httpx` before even
launching the browser. The scraper code is the most defensive of all — it even
simulates human-like mouse movements and scrolling.

**8. Procura Pecas** — VTEX e-commerce store. Navigated to `/{SKU}?map=ft`,
extracted product cards with VTEX selectors, preferred PIX price. Clean and
simple scraper. SKU found via `REF:.{SKU}` pattern in titles.

**9. eBay** — Global marketplace. Searched
`/sch/i.html?_nkw={SKU}&_sacat=6028` (auto parts category), used 4 fallback
DOM strategies for extraction (`.s-item` -> `srp-results li` ->
`data-viewport` -> generic container), parsed USD/BRL/EUR. Had custom block
detection that allowed hidden CAPTCHA markup when results were visible.

---

## Root Causes & Solutions

### Problem 1: Melibox 403 (Highest Priority)

**Root Cause:** The Azure Container App's IP is being blocked by
Melibox/Cloudflare at the login entry page. The scraper works perfectly from
local/allowed networks (17 exact rows returned locally on 2026-05-13), but
production gets `403 Forbidden` before credentials can even be used.

**Solutions:**

1. **Residential/rotating proxy** — Configure `PROXY_URLS` with Brazilian
   residential proxies. The infrastructure already supports it
   (`PROXY_ROTATION_ENABLED` + `BaseScraper` proxy integration), but
   `PROXY_URLS` is currently empty in production.
2. **Allowlist the Azure outbound IP** — If Melibox supports IP allowlisting,
   add the Container App's egress IP.
3. **Per-SKU context rotation** — Already implemented
   (`MELIBOX_ROTATE_CONTEXT_PER_SKU=true`) to spread requests across different
   proxy exits.

### Problem 2: Mercado Livre Smoke SKU Stale

**Root Cause:** The smoke test SKU `06K907811B` previously returned results but
no longer does. ML's search index is volatile — product listings come and go.

**Solutions:**

1. **Refresh the smoke SKU** — Find a new positive SKU from a known-active
   listing (e.g., `51766536` returned 5 exact results on 2026-05-19).
2. **Rotating SKU pool** — Already implemented in
   `scripts/production_sku_pool.py` for random 5-SKU samples. Use this for
   smoke tests instead of a single hardcoded SKU.

### Problem 3: GoParts Cloudflare (Archived)

**Root Cause:** Cloudflare issues `cf-mitigated: challenge` headers. Headless
Chromium cannot solve Cloudflare Turnstile challenges. Even with stealth mode,
human-like delays, and analytics blocking, the browser gets challenged.

**Solutions:**

1. **Paid proxy with Cloudflare bypass** — Services like Bright Data, Oxylabs,
   or ScraperAPI can provide pre-warmed sessions that pass Cloudflare.
2. **Official API / data partnership** — GoParts may have a data API or
   affiliate program. Browser scraping is not sustainable against aggressive
   Cloudflare.
3. **Undetected-chromedriver or Camoufox** — Replace Playwright Chromium with a
   patched browser build that passes fingerprint checks. Requires testing.

### Problem 4: Procura Pecas Cloudflare (Archived)

**Root Cause:** Same Cloudflare managed challenge issue as GoParts. Even the
public VTEX product-search API endpoint is behind Cloudflare.

**Solutions:**

1. **Same proxy solution as GoParts** — Residential proxy with warm sessions.
2. **VTEX API direct access** — VTEX stores have a structured API
   (`/api/catalog_system/`). If Procura Pecas' VTEX API isn't behind
   Cloudflare, we can bypass the browser entirely with HTTP requests.
3. **Browser fingerprint patching** — Same as GoParts.

### Problem 5: eBay Access Denied (Archived)

**Root Cause:** eBay serves "Access Denied" / "Pardon Our Interruption"
interstitials to datacenter IPs. The scraper code handles this gracefully but
cannot bypass it.

**Solutions:**

1. **eBay Partner Network API** — eBay has a Browse API / Finding API through
   their developer program. Free tier allows product search. This is the most
   sustainable approach.
2. **Residential proxy** — Same proxy infrastructure that would fix Melibox and
   GoParts would also fix eBay.
3. **Lower priority** — eBay is international (USD) and the business primarily
   needs Brazilian sources. Consider deprioritizing.

---

## Recommended Action Plan

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| **P0** | Configure residential proxy (`PROXY_URLS`) | Medium | Unblocks Melibox, GoParts, ProcuraPecas, eBay |
| **P1** | Replace ML smoke SKU with `51766536` | Low | Fixes ML monitoring false alarms |
| **P2** | Test GoParts + ProcuraPecas with proxy | Low | Potentially recovers 2 sources |
| **P3** | Evaluate eBay Browse API | Medium | Sustainable international source |
| **P4** | Explore VTEX API for ProcuraPecas | Medium | Browser-free, faster, more reliable |

---

## Key Takeaway

The single highest-leverage improvement is **adding residential proxy URLs to
production**. The proxy infrastructure is already built (`BaseScraper`,
`proxy_manager.py`, env vars `PROXY_ROTATION_ENABLED` + `PROXY_URLS`), it just
needs actual proxy endpoints configured. This one change could recover **4 out
of 4** blocked/archived scrapers.

---

## Technical Reference

### Scraper Registry

- Active: `src/scrapers/__init__.py` → `SCRAPER_REGISTRY`
- Archived: `src/scrapers/__init__.py` → `ARCHIVED_SCRAPER_REGISTRY`
- Mock: `MOCK_SCRAPERS=true` enables `MockGMScraper` for CI/local testing

### Anti-Bot Baseline (all scrapers)

- Browser profile: locale `pt-BR`, timezone `America/Sao_Paulo`, desktop
  viewport, Chromium user-agent
- Session persistence: `browser_states/{site}_state.json`
- Pacing: `SCRAPE_DELAY_MIN/MAX` between SKUs, `SCRAPER_ACTION_DELAY_*` within
  pages
- Block detection: HTTP 403/429, CAPTCHA/Cloudflare/Turnstile text and elements
- Retry: `ANTI_BOT_RETRY_ATTEMPTS` with exponential backoff, then honest
  `blocked` status

### Status Vocabulary

| Status | Meaning |
|--------|---------|
| `success` | Exact priced results found |
| `not_found` | No matching products on the site |
| `no_price` | Exact product exists but no usable price (out of stock) |
| `blocked` | Anti-bot / access restriction prevented scraping |
| `error` | Unexpected failure (auth, timeout, DOM change, etc.) |
| `timeout` | Operation exceeded time budget |
