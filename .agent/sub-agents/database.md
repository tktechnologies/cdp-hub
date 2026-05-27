# Database Agent (Platform)

## Ownership

PostgreSQL models, migrations, and query patterns in **either** service — never a shared DB package.

## Read First

- Scraper: `scrapers/alembic/`, `scrapers/src/models/database.py`
- StokAPI: `muvstok-api/alembic/`, `muvstok-api/app/db/models.py`
- [muvstok-api/.agent/skills/muvstok-add-migration/SKILL.md](../../muvstok-api/.agent/skills/muvstok-add-migration/SKILL.md)

## Expected Output

- Migration files and upgrade/downgrade notes.
- Backfill or rollout steps if needed.
- Validation: alembic upgrade head in target service.

## Boundaries

One service per task unless explicitly cross-service. Do not mix scraper job tables with `muvstok_*` tables.
