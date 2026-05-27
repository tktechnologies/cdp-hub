# Mercado Livre Scraper

**Site ID:** `ml`  
**Code:** `src/scrapers/mercadolivre.py`  
**Source:** `https://lista.mercadolivre.com.br`

## Story

Mercado Livre is useful and noisy. Search returns many priced cards quickly, but
many are nearby products, ads, tools, or broad catalog matches. ML is a candidate
source, not a truth source; exact matching is everything.

## What We Want

- Open `https://www.mercadolivre.com.br`, set CEP `80220001` when prompted.
- Search URL: `https://lista.mercadolivre.com.br/{sku}_NoIndex_True`.
- Only new/non-used candidates.
- Exact SKU in title for `success`.
- BRL price, listing URL, seller when visible.

## Current DOM Map

- Cards: `li.ui-search-layout__item`, `div.ui-search-result`,
  `div.ui-search-result__wrapper`, `li.poly-card`.
- Title:
  `h2.ui-search-item__title`, `h2.poly-component__title`, title links.
- Price:
  `span.andes-money-amount__fraction` and optional cents.
- Seller:
  official-store or seller-labeled spans.

## Known Evidence

2026-05-13 all-scraper probe:

- `06K907811B` -> `success`, multiple exact BRL results; first observed price
  BRL 298.33.
- `5U6867287Y20` -> `not_found` with priced non-exact candidates.

## Failure Modes

- Sponsored/related cards often rank above exact-SKU listings; scanning only the
  first 10 cards misses valid prices (exact matches may start around index 13+).
  The scraper scans the full results page (bulk DOM extraction, up to 120 cards)
  and returns every priced listing found, not just the first hit.
- Ads and catalog cards can be plausible but non-exact.
- ML may change classes often; price may live in `andes-money-amount` fraction +
  cents, `aria-label` (e.g. `1801 reais`), or poly-card text.

## Agent Moves

- Never loosen title exactness for ML.
- Add parser fixtures for one exact title and one noisy false positive.
- Treat non-exact priced results as diagnostic only.
