---
name: scraper-source-playbooks
description: Use source-specific scraper playbooks to debug, improve, or validate one supplier scraper at a time.
---

# Scraper Source Playbooks Skill

Use when debugging, improving, or validating a specific supplier scraper.

## Read First

1. `scrapers/AGENTS.md` and `.agent/index.md`
2. `docs/SCRAPER_AGENT_PLAYBOOK.md`
3. The relevant playbook under `docs/scrapers/`
4. The matching file under `src/scrapers/`
5. `src/scrapers/base.py`

Only load one scraper's playbook unless the task is cross-source.

## Source Map

| Site | Playbook |
|---|---|
| `gm` | `docs/scrapers/gm.md` |
| `ml` | `docs/scrapers/mercadolivre.md` |
| `vw` | `docs/scrapers/vw.md` |
| `eu` | `docs/scrapers/eu-imports.md` |
| `pecadireta` | `docs/scrapers/pecadireta.md` |
| `melibox` | `docs/scrapers/melibox.md` |

Archived (reference only): `goparts`, `procurapecas`, `ebay`

## Rules

- Never weaken exact SKU matching.
- Product + no price = `no_price`, not `not_found`.
- CAPTCHA/access denied = `blocked`. Do not bypass.
- Preserve source currency.
- Use headed Playwright DOM evidence before changing selectors.
- Keep screenshots, cookies, browser state, and secrets out of git.

## Verification

```bash
uv run --extra dev pytest tests/test_scrapers -v
uv run --extra dev ruff check src/scrapers tests/test_scrapers
```
