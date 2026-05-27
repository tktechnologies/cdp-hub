# ProcuraPeças Scraper

> **Archived (2026-05-13):** not in the active `SCRAPER_REGISTRY`. Source file kept for reference.

**Site ID:** `procurapecas`  
**Code:** `src/scrapers/procurapecas.py`  
**Source:** `https://procurapecas.com.br`

## Story

ProcuraPeças is a VTEX-style store. It is cleaner than a marketplace when it
renders, because `REF` codes can give strong SKU evidence. The tricky part is
that repeated live requests can trigger an anti-bot box.

## What We Want

- Direct URL: `https://procurapecas.com.br/{sku}`.
- Product cards with all visible prices, preferably PIX/best price and list
  price evidence.
- Seller normalized to `Procura Peças` unless the page exposes otherwise.
- `blocked` when CAPTCHA/turnstile appears.

## Current DOM Map

- Product candidates:
  `[class*="productCard"]`, `[class*="product-summary"]`,
  `[class*="gallery-item"]`, `a[href$="/p"]`.
- Price patterns: `R$ ...`, PIX/a vista labels.
- SKU evidence: title pattern `REF:.{sku}` or equivalent `REF`.

## Known Evidence

2026-05-13 all-scraper probe:

- `5U6867287Y20` -> `blocked` after repeated live requests.
- `06K907811B` -> `blocked` after repeated live requests.

Earlier headed runs returned clean `not_found` for `06K907811B`.

## Failure Modes

- Anti-bot box appears after repeated probes. Do not bypass it.
- VTEX cards may render after fixed waits; avoid tight DOM loops.
- Positive `REF` fixtures are still needed.

## Agent Moves

- Use headed mode for DOM evidence when unblocked.
- If blocked, stop and report `blocked`.
- Capture static card HTML before adding parser tests.
