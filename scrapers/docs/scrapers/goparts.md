# GoParts Scraper

**Site ID:** `goparts`  
**Code:** `src/scrapers/goparts.py`  
**Source:** `https://goparts.com.br`
**Status:** Archived on 2026-05-13. Not in the active scraper registry.

## Story

GoParts should be broad and valuable, but it is the stubborn source. Heavy
analytics and Cloudflare can make browser sessions hang. Treat it as a fragile
integration where the current browser scraper may need replacement by an API or
more deliberate network strategy.

## What We Want

- Search URL: `https://goparts.com.br/busca/{sku}`.
- Product/table rows with price, seller, availability.
- Explicit `timeout` or `blocked` when the site refuses to cooperate.

## Current DOM Map

- Search path: `/busca/{sku}`.
- Candidate cards:
  `.product-card`, `[class*="product"]`, `[class*="resultado"]`,
  `[class*="item-busca"]`.
- Table fallback: `.list-of-parts table`, `table`.
- Product link fallback: `a[href*="/peca/"]`, `a[href*="/produto/"]`.

## Known Evidence

2026-05-13 all-scraper probe:

- `5U6867287Y20` -> `timeout`.
- `06K907811B` -> `timeout`.

## Failure Modes

- Playwright can hang despite blocked analytics/images/fonts.
- `domcontentloaded` can be unreliable; current code uses `wait_until="commit"`.
- Cloudflare may require headed diagnosis.

## Agent Moves

- Keep timeouts explicit. Do not fake `not_found`.
- Consider public/API-backed search before more DOM scraping.
- If maintaining browser scraping, inspect network and route blocking before
  changing selectors.
