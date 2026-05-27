# Scraper Field Work Skill

Use when running, debugging, documenting, or improving a live supplier scraper.

## Read First

1. `scrapers/AGENTS.md` and `.agent/index.md`
2. `docs/SCRAPER_FIELD_GUIDE.md`
3. `docs/SCRAPER_AGENT_PLAYBOOK.md`
4. Target playbook under `docs/scrapers/`
5. Target scraper under `src/scrapers/`
6. `src/scrapers/base.py`

## Local Discovery

```bash
docker compose up -d postgres redis
uv run --extra dev alembic upgrade head

MOCK_SCRAPERS=false PROXY_ROTATION_ENABLED=false \
  uv run --extra dev python scripts/demo_scraper_runs.py \
  --timeout-seconds 75
```

## Production Validation

Use `scripts/validate_local_scrapers.py` with a curated manifest from `docs/validation/local_scraper_manifest.example.json`.

## Rules

- Never weaken exact SKU matching.
- Anti-bot blocks → explicit `blocked`, not `not_found`.
- Keep source currency; no mixed-currency `best_price`.
- Prefer official APIs when they give the required data.
- Never commit customer data, screenshots, cookies, or credentials.

## After Changes

Update `docs/SCRAPER_FIELD_GUIDE.md`, `docs/CHANGELOG.md`, and relevant `docs/SPECS/`.
