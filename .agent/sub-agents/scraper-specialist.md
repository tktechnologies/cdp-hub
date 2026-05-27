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
- Cache and callback notes if behavior changed.

## Boundaries

Do not change StokAPI routes, Muvstok client, or `cdp_stokapi.json`. Do not edit `n8n/src/` router dispatch without platform n8n skill.
