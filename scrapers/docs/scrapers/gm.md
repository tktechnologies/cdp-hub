# GM Chevrolet Scraper

**Site ID:** `gm`  
**Code:** `src/scrapers/gm.py`  
**Source:** `https://www.pecachevrolet.com.br`

## Story

GM is a public Peça Chevrolet portal where the product page is not the whole
truth. The real operational value is hidden in the dealer-offer rows after a
location/CEP session exists. Treat it like walking into a dealer counter: first
prove location, then open the part detail, then read every dealer offer.

## What We Want

- Direct search URL:
  `https://www.pecachevrolet.com.br/pesquisa/?nomepeca=&grupo=&nomeveiculo=&ano=&numeropeca={sku}`
- Exact product detail URL when available.
- One `PartResult` per dealer/shop price.
- Dealer name, city, distance when visible.
- Positive BRL price for `success`; exact product without price is `no_price`.

## Current DOM Map

- Product link candidates: `/peca/{sku}/...`, `/p`, `/produto`.
- Detail title: `h1`, `h1.product-name`, `h1[class*='productName']`.
- Current dealer row: `.tab-precos-row-2024`.
- Dealer name: `.concessionaria-name-2024`.
- Dealer city: `.concessionaria-cidade-2024`.
- Dealer distance: `.concessionaria-distancia-2024`.
- Price value: `.concessionaria-preco-2024-value`.
- Availability signal: row text containing `COMPRAR`.

## Known Evidence

2026-05-13 headed run:

- `22781768` -> `success`, three exact dealer prices:
  - AUTOESTE, BRL 2055.43
  - AUTUS, BRL 1015.89
  - BRAGA, BRL 1268.78
- `5U6867287Y20` -> `not_found`.
- `06K907811B` -> `not_found`.

## Failure Modes

- Default CEP `01001-000` can remain visible even when the page still shows
  dealer prices. Do not rely only on localStorage.
- Product page can render prices without `R$` symbol because label and value
  are separate DOM nodes.
- Hidden CEP inputs exist; use visible inputs only.

## Agent Moves

- Before selector changes, run headed DOM probe and inspect
  `.tab-precos-row-2024`.
- Preserve multi-dealer rows. Do not collapse to one result.
- If a product page exists but no price row appears, return `no_price`.
