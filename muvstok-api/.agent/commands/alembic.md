# Alembic Commands

## Upgrade

```bash
uv run alembic upgrade head
```

Requires `DATABASE_URL` for the target environment.

## Migration Safety

- Keep SQLAlchemy models and Alembic migrations in sync.
- Do not store raw secrets in migrations or seed data.
- Validate migration behavior against Azure-hosted PostgreSQL when the change affects production schema.
