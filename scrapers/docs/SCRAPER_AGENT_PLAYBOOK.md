# Scraper Agent Playbook

**Created:** 2026-05-13  
**Purpose:** Onboard maintenance agents to the story, contract, and field moves
for each scraper.

This repo is a scraper service, not a generic automation playground. Every
scraper exists to answer one operational question: for this exact automotive
SKU, what source-visible product, seller, price, currency, condition,
availability, and URL can we trust enough to persist?

## Agent North Star

Use exact SKU evidence as the spine. A nice price without exact SKU evidence is
diagnostic data, not a `success`. Exact products without positive price or usable
stock are preserved as `no_price` so operators can see “Sem estoque” evidence.
Anti-bot or CAPTCHA is `blocked`; do not bypass it. Unexpected code failures are
`error`. Empty exact search is `not_found`.

## Source Playbooks

Read only the scraper you are touching:

| Site | File | Role |
|---|---|---|
| `gm` | [GM Chevrolet](scrapers/gm.md) | Official GM/Chevrolet dealer prices, multi-dealer detail rows. |
| `ml` | [Mercado Livre](scrapers/mercadolivre.md) | Noisy marketplace; strict title matching matters. |
| `vw` | [Volkswagen](scrapers/vw.md) | Official VW store; SKU evidence often in title and product URL. |
| `eu` | [EU Imports](scrapers/eu-imports.md) | FastParts table source, USD/EUR, Mercedes normalization. |
| `pecadireta` | [PeçaDireta](scrapers/pecadireta.md) | Marketplace cards; product may exist but be out of stock. |
| `melibox` | [Melibox](scrapers/melibox.md) | Authenticated Sellerbox portal; **advProductPosition** (Frase/Palavra + Enviar) and table row prices. |

Archived sources (code/playbook kept; **not** in `SCRAPER_REGISTRY`): `goparts`, `procurapecas`, `ebay` — see `docs/scrapers/goparts.md`, `procurapecas.md`, `ebay.md`.

## Shared Workflow

1. Read `.agent/prompts/agent-startup.md`, `.agent/rules.md`,
   and `.agent/skills/scraper-source-playbooks/SKILL.md`.
2. Read the relevant `docs/scrapers/{site}.md`, `src/scrapers/{site}.py`,
   `src/scrapers/base.py`, and focused tests under `tests/test_scrapers/`.
3. Preserve `BaseScraper` interface: `site_id`, `site_name`, `login()`,
   `search_sku()`.
4. Prefer DOM evidence from headed Playwright before changing selectors.
5. Add parser/status tests using static snippets or pure helpers. Live sites are
   evidence, not CI fixtures.
6. Update docs and artifacts when behavior changes.

## Demo SKU Map From 2026-05-19

| Site | SKU | Notes |
|---|---:|---|
| `gm` | `93240598` | Supplied validated demo SKU. |
| `vw` | `5X9827550A` | Supplied validated demo SKU. |
| `procurapecas` | `51766536` | Demo-only archived source. |
| `ml` | `51766536` | Supplied validated demo SKU. |
| `eu` | `03L115562` | Supplied validated demo SKU. |
| `ebay` | `5473368` | Demo-only archived source. |
| `goparts` | `7091011` | Demo-only archived source. |
| `pecadireta` | `7091011` | Supplied validated demo SKU. |
| `melibox` | `51766536` | Requires account credentials and matching inventory/listing. |

Latest artifacts: `docs/validation/latest_production_*`

## Anti-Bot Posture

We prevent avoidable bot signals; we do not defeat access controls.

- Use `BaseScraper.initialize()` for shared browser profile, user-agent
  selection, locale/timezone, session state, proxy assignment, and
  headed/headless config.
- Leave `BROWSER_USER_AGENTS=[]` unless a source has a reason to rotate
  explicit Chromium-compatible user agents. A mismatched Firefox/Safari UA on a
  Chromium browser is worse than no rotation.
- Keep `scrape_delay_min` / `scrape_delay_max` for inter-SKU pacing.
- Use `_action_delay()` around navigation and major interactions.
- Detect HTTP `403` / `429`, Cloudflare/CAPTCHA/turnstile/access-denied and
  return `blocked` after the bounded anti-bot backoff settings are exhausted.
- After the 2026-05-19 live probes, expect GoParts and Procura Peças to return
  Cloudflare managed challenges from this network. Let the status be honest.
- eBay can include hidden challenge markup while still showing real result rows;
  use its site-specific detector rather than the shared hidden-element check.

## Demo Commands

Local discovery:

```bash
UV_CACHE_DIR=/tmp/uv-cache MOCK_SCRAPERS=false PROXY_ROTATION_ENABLED=false \
  uv run --extra dev python scripts/demo_scraper_runs.py --timeout-seconds 75
```

Production smoke:

```bash
uv run python scripts/production_scraper_curl_smoke.py
```
