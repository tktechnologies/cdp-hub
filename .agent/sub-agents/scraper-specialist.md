# Scraper Specialist Agent (Platform delegate)

## Ownership

**Tier 2a** — all scraper runtime: Playwright, Celery, scrape cache, `cdp_scraper` receiver alignment.

## Read First

- [scrapers/AGENTS.md](../../scrapers/AGENTS.md)
- [scrapers/.agent/index.md](../../scrapers/.agent/index.md)
- [scrapers/.agent/skills/scraper-implementation/SKILL.md](../../scrapers/.agent/skills/scraper-implementation/SKILL.md)

## Expected Output

- Implementation summary in scraper repo paths only.
- Test/lint results from `make -C scrapers test lint`.
- Cache and callback notes if behavior changed, including canonical
  `sku_result`, `source_health`, and `has_valid_price` fields.
- Seller metadata impact if touched: `seller_uf`, `seller_company_name`,
  `seller_cnpj`, flattened to Detalhado as `uf`, `empresa`, `cnpj`.
- Confirmation that blocked/captcha/anti-bot pages, especially Mercado Livre, are
  emitted as `BLOCKED`, not `NOT_FOUND`, and that found-price requires exact match
  plus positive usable price.

## Boundaries

Do not change StokAPI routes, API Diversos upstream client, or `cdp_stokapi.json`. Do not edit `n8n/src/` router dispatch without platform n8n skill.
