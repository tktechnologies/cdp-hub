# Scraper agent rules

Scraper Tier 2 rules. For platform-wide n8n rules see `../../.agent/boundaries/n8n.md`.

## Scope

- This repo is the scraper service only.
- CDP n8n workflows at monorepo `n8n/workflows/` (`cdp_router`, `cdp_scraper`); router Code in `n8n/src/`.
- Do not add Muvstok worker logic or StokAPI API routes here.

## Scraper contracts

- Every scraper inherits `BaseScraper`: `site_id`, `site_name`, `login`, `search_sku`.
- Register production scrapers in `SCRAPER_REGISTRY` (`src/scrapers/__init__.py`).
- Keep browser states and screenshots out of git.

## Data contracts

- Public models: `src/models/schemas.py`; persistence: `src/models/database.py`.
- Required result fields per `docs/SCRAPER_FIELD_GUIDE.md` and `src/models/schemas.py`.
- Exact SKU match after normalization; EU/Mercedes trim; ML new items only.
- Callback reporting fields are `sku_result`, `source_health`, and
  `has_valid_price`.
- Seller/location reporting fields are `seller_uf`, `seller_company_name`, and
  `seller_cnpj`; Google Sheets output columns are `uf`, `empresa`, `cnpj`.
  `estado` is not a canonical output field.
- `FOUND_PRICE` requires exact SKU match plus positive usable price.
  `NO_PRICE`, `NOT_FOUND`, `BLOCKED`, `TIMEOUT`, `ERROR`, and `NOT_QUERIED`
  remain separate outcomes and are not found-price successes.
- Anti-bot/captcha/403/access-denied pages, especially Mercado Livre, are
  `BLOCKED`, not `NOT_FOUND`.

## Engineering

- Python 3.12+, async-first, Pydantic at boundaries, `structlog` only.
- Config via `src/config.py` only.
- Add/update tests for behavior changes.

## n8n (this service)

- **Receiver owner:** `cdp_scraper.json`, webhook `scraper-result`.
- **Router JSON** in `../../n8n/workflows/`; **router Code** edited in `../../n8n/src/` only.
- Never publish to live n8n without user approval.

## Security

- Never commit `.env`, credentials, browser state, customer data.
- API: `X-API-Key`; callbacks: `X-Webhook-Secret`.
