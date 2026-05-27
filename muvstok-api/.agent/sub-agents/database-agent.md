# Database Agent

## Ownership

SQLAlchemy models, Alembic migrations, and repositories.

## Read First

- `.agent/rules.md`
- `.agent/skills/muvstok-add-repository/SKILL.md`
- `.agent/skills/muvstok-add-migration/SKILL.md`
- `specs/004-database-design.md`
- `app/db/models.py`
- `app/db/migrations/`
- `app/repositories/`

## Expected Output

- Schema or repository changes.
- Migration safety notes.
- Validation performed against local or Azure database.
- Any data compatibility risk.

## Boundaries

Do not change API contracts or worker orchestration unless explicitly assigned.
