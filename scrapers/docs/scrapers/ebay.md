# eBay Scraper

> **Archived (2026-05-13):** not in the active `SCRAPER_REGISTRY`. Source file kept for reference.

**Site ID:** `ebay`  
**Code:** `src/scrapers/ebay.py`  
**Source:** `https://www.ebay.com`

## Story

eBay is the volatile international marketplace. It can return useful USD/BRL/EUR
prices, but access-denied and CAPTCHA surfaces can look like empty results if
the scraper is careless. Honesty matters more than volume.

## What We Want

- Search URL:
  `https://www.ebay.com/sch/i.html?_nkw={sku}&_sacat=6028`.
- Exact SKU evidence from listing title.
- Price and source currency.
- Condition from listing text.
- `blocked` on access denied, CAPTCHA, Cloudflare/turnstile.

## Current DOM Map

- Result containers: `.s-item`, `.srp-results li`, `[data-viewport]`.
- Product links: `a[href*="/itm/"]`.
- Price patterns: `R$`, `US $`, `$`, `EUR`, `€`.
- Condition: `new`, `brand new`, `used`, `pre-owned`, localized variants.

## Known Evidence

2026-05-13 all-scraper probe:

- `5U6867287Y20` -> `blocked`.
- `06K907811B` -> `blocked` after extraction because challenge indicators were
  present.

Earlier headed validation showed `06K907811B` can produce a BRL success when the
site does not challenge.

## Failure Modes

- DOM class churn is common.
- Access denied can render with list-like elements.
- Price ranges need first-price parsing.

## Agent Moves

- Check blocked status after navigation and before trusting extracted rows.
- Do not store results when challenge indicators are present.
- Keep parser tests independent of live eBay.
