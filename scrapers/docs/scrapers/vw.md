# Volkswagen Scraper

**Site ID:** `vw`  
**Code:** `src/scrapers/vw.py`  
**Source:** `https://pecas.vw.com.br`

## Story

VW is the calm official store. It tends to render useful product cards, but SKU
evidence can be in the title and URL rather than a clean data field. The agent’s
job is to treat the card as a coherent object: title, URL, price, seller text,
and availability together.

## What We Want

- Direct URL: `https://pecas.vw.com.br/todas-categorias?q={sku}`.
- Exact SKU match from title or product URL.
- BRL price, product title, product URL, seller/dealer text, availability.
- `success` only when exact SKU and positive price exist.

## Current DOM Map

- Product cards:
  `[class*="productCard"]`, `[class*="product-summary"]`,
  `[class*="gallery-item"]`, `article`, `li[class*="product"]`.
- Product URL: `a[href*="/produto"]`.
- Price: `R$ ...` in card text.
- Seller text often includes `Vendido e entregue por`.
- Exact evidence can be repeated in URL:
  `/produto/...-{sku}-{sku}/...`.

## Known Evidence

2026-05-13 live runs:

- `5U6867287Y20` -> `success`, BRL 683.30.
- `06K907811B` -> `success`, BRL 8545.57.
- `22781768` -> `not_found`.

## Failure Modes

- Old logic marked exact cards false when SKU extraction was partial.
- CEP input is not always visible; search can still return prices.
- Promotional banner prices (`FRETE30`, `R$ 200`) can appear in page text; keep
  extraction scoped to product cards.

## Agent Moves

- Validate exactness against title and product URL, not only an extracted SKU
  field.
- When cards appear visually but results are empty, inspect card selectors and
  link extraction first.
