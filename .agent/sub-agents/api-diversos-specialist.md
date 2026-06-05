# API Diversos Specialist Agent (Platform delegate)

## Ownership

**Tier 2b** - API Diversos/StokAPI runtime: FastAPI job API, Redis Streams
worker, upstream stock client, persistence, callbacks, and `cdp_stokapi` receiver
alignment.

## Read First

- [muvstok-api/AGENTS.md](../../muvstok-api/AGENTS.md)
- [muvstok-api/.agent/index.md](../../muvstok-api/.agent/index.md)
- [muvstok-api/.agent/skills/README.md](../../muvstok-api/.agent/skills/README.md)
- [muvstok-api/.agent/memory/implementation-state.md](../../muvstok-api/.agent/memory/implementation-state.md)

## Expected Output

- Implementation summary in `muvstok-api/` paths only.
- Specs or service memory updated when behavior changes.
- Validation results from `make check-muvstok` or targeted service checks.
- Callback and receiver impact if behavior changed, including canonical
  `sku_result`, `source_health`, and `has_valid_price` fields.
- Sheets seller metadata impact if touched: `vendedor`, `uf`, `empresa`, `cnpj`;
  raw `estado` aliases normalize to `uf`.
- Confirmation that processing `succeeded` is not treated as price-found unless
  `sku_result = FOUND_PRICE` and `has_valid_price = true`.

## Boundaries

Do not change Playwright scrapers, scrape cache, or `cdp_scraper.json`. Do not
edit `n8n/src/` router dispatch without platform n8n ownership.
