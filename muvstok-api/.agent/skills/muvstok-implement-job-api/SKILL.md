---
name: muvstok-implement-job-api
description: Implement or update Muvstok FastAPI job API behavior. Use when changing routes, dependencies, request schemas, response schemas, API key auth, idempotency behavior, job submission, job inspection, or OpenAPI-facing contracts in app/api, app/schemas, or app/services/job_service.py.
---

# Muvstok Job API

## Overview

Use this skill to keep API changes aligned with the job ingestion contract and the route -> service -> repository/client architecture.

## Read First

- `.agent/rules.md`
- `.agent/memory/implementation-state.md`
- `specs/002-api-contract.md`
- `specs/006-harness-engineering.md`
- `app/api/dependencies.py`
- `app/api/routes/jobs.py`
- `app/schemas/requests.py`
- `app/schemas/responses.py`
- `app/services/job_service.py`

## Workflow

1. Confirm whether the public API contract changes.
2. Keep route handlers thin; move business rules into services.
3. Put request validation in Pydantic schemas when it belongs at the boundary.
4. Preserve `X-API-Key` protection on protected endpoints.
5. Preserve idempotency behavior for duplicate `idempotency_key` values.
6. Preserve SKU normalization and `MAX_SKUS_PER_JOB`.
7. Keep response models explicit and stable.
8. Add structured logs in services, not noisy route-level logs.
9. Update specs and `.agent/` memory when behavior changes.

## Validation

- Run `uv run ruff check .` after Python edits.
- Run `uv run mypy .` after typed interface changes.
- Run `uv run pytest` when tests exist or were added.
- Run `bash scripts/check_specs.sh` after spec changes.
- Record Azure validation status before calling the task done.

## Watch Points

- `GET /api/v1/muvstok/health` is unauthenticated.
- `POST /api/v1/muvstok/jobs` and `GET /api/v1/muvstok/jobs/{job_id}` are protected.
- `app/api/routes/muvstok.py` is currently only a compatibility placeholder and is not included in `app/main.py`.
