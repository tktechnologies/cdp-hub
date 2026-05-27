---
name: muvstok-add-repository
description: Add or update Muvstok SQLAlchemy repositories and database query boundaries. Use when implementing app/repositories modules, adding persistence methods, changing transaction behavior, mapping database models to response/domain models, or improving large-job database access.
---

# Muvstok Repository

## Overview

Use this skill to keep persistence logic inside repositories and protect large-job behavior, transaction safety, and resumability.

## Read First

- `.agent/rules.md`
- `.agent/memory/implementation-state.md`
- `specs/004-database-design.md`
- `app/db/models.py`
- Existing repository in `app/repositories/`
- Calling service in `app/services/`

## Workflow

1. Identify the service use case and the exact data contract needed.
2. Keep SQLAlchemy queries inside repositories.
3. Use async `AsyncSession` patterns already in the repo.
4. Batch large SKU operations with `job_item_batch_size` style patterns.
5. Keep commits deliberate; avoid hidden commits when a service needs a larger transaction.
6. Map DB models to response/domain models at the boundary already used by the codebase.
7. Preserve indexes and uniqueness assumptions from the schema.
8. Add or update tests for query behavior when the test surface exists.
9. Update `.agent/memory/implementation-state.md` if a placeholder repository becomes real.

## Validation

- Run `uv run ruff check .`.
- Run `uv run mypy .`.
- Run `uv run pytest` for repository tests when present.
- Validate database behavior in Azure when it affects production state.

## Watch Points

- `JobRepository.create_job()` currently commits before queue publish; recoverability matters.
- Many repositories are placeholders and should be updated carefully with focused methods.
- Never store raw secrets in repository methods or fixture data.
