# PeçaDireta Scraper

**Site ID:** `pecadireta`  
**Code:** `src/scrapers/pecadireta.py`  
**Source:** `https://www.pecadireta.com.br`

## Story

PeçaDireta is a marketplace shelf. It can show exact products even when nobody
has inventory. The crawler must behave like a buyer scanning a shelf: identify
the actual product card, ignore site furniture, then decide whether price exists.

## What We Want

- Direct search URL:
  `https://www.pecadireta.com.br/procurar/pecas?query={sku}`
- Product cards and product detail URLs under `/produto/{brand}/{sku}`.
- Exact out-of-stock cards persisted as `no_price` **unless** we can open the
  `/produto/` page and recover a price from `itemprop` / body text.
- Never open social, WhatsApp, help, footer, pagination, or `/procurar` links
  as product pages.

## Current DOM Map

- Product card: `div.card-produto-horizontal`.
- Product link: `a[href^="/produto/"]`.
- Product title: link text or card heading.
- Out-of-stock text:
  `Produto temporariamente fora de estoque`.
- SKU evidence: title contains SKU or URL path `/produto/{brand}/{sku}`.

## Known Evidence

2026-05-13 headed run:

- `5U6867287Y20` -> `no_price`, exact product:
  `/produto/volkswagen/5u6867287y20?obsoleto=0`.
- `06K907811B` -> `no_price`, exact product:
  `/produto/volkswagen/06k907811b?obsoleto=0`.
- `22781768` -> `not_found`.

## Failure Modes

- Generic selectors can pick Facebook, Instagram, LinkedIn, WhatsApp,
  pagination, footer, and category links.
- The page title typo `Resutados` is normal and should not matter.
- No visible price does not mean no product; inventory text decides `no_price`.

## Agent Moves

- Extract listing cards first so out-of-stock products are preserved.
- Only navigate to same-origin `/produto/` URLs.
- Add tests for product-path SKU extraction and query-string non-matches.
