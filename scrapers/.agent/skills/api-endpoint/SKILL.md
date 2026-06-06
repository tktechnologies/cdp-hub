---
name: scraper-api-endpoint
description: Change the Scraper FastAPI API, request and response schemas, callback behavior, routes, orchestrator contract, or API tests.
---

# Skill: Change The FastAPI Scraper API

Use when adding/changing endpoints, request/response schemas, callback behavior, or API logic.

## Source Files

- `src/api/routes/` — REST endpoints (`jobs.py`, `dispatch_runs.py`, …)
- `src/models/schemas.py` — Pydantic contracts
- `src/services/orchestrator.py` — job execution
- `src/tasks/scrape_jobs.py` — Celery worker execution
- `tests/test_api/` — route tests

## Workflow

1. Read current route and schema before editing.
2. Public contract change → update Pydantic schemas first.
3. Authenticated endpoints behind `verify_api_key`; health endpoints unauthenticated.
4. Business logic in service layer, not routes.
5. Explicit HTTP status codes and typed `response_model`.
6. Update tests for auth, validation, success, and failure.
7. If job/result shape changes → update orchestrator persistence and integration tests.

## Tests

```bash
uv run pytest tests/test_api -v
uv run pytest tests/test_services/test_orchestrator.py -v
```

## Done When

- OpenAPI reflects intended contract.
- Auth tested.
- Existing data contracts still serialize cleanly.
