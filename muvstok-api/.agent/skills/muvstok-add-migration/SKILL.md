---
name: muvstok-add-migration
description: Add or update Muvstok SQLAlchemy models and Alembic migrations. Use when changing app/db/models.py, app/db/migrations, database tables, enums, indexes, constraints, JSONB fields, or PostgreSQL schema behavior.
---

# Muvstok Migration

## Overview

Use this skill to keep model and migration changes explicit, reversible, and aligned with PostgreSQL as the durable source of truth.

## Read First

- `.agent/rules.md`
- `.agent/memory/implementation-state.md`
- `specs/004-database-design.md`
- `app/db/models.py`
- `app/db/migrations/env.py`
- Existing migration versions

## Workflow

1. Update SQLAlchemy models and enums first.
2. Add an Alembic migration with explicit upgrade and downgrade steps.
3. Keep enum creation and drop behavior explicit for PostgreSQL.
4. Add indexes for worker and API lookup paths.
5. Add uniqueness constraints for idempotency and duplicate SKU prevention.
6. Use JSONB for raw Muvstok responses and metadata.
7. Never include raw secrets or production data in migrations.
8. Update specs and `.agent/memory/implementation-state.md` when schema reality changes.

## Validation

- Run `uv run ruff check app/db app/repositories`.
- Run `uv run mypy app`.
- Run `uv run alembic upgrade head` against the intended test database.
- Run Azure-hosted PostgreSQL validation for production-impacting schema changes.

## Watch Points

- Nullable `idempotency_key` with a unique constraint allows multiple nulls in PostgreSQL.
- Large jobs require efficient indexes and batched inserts.
- Downgrades should drop dependent tables and indexes before enum types.
