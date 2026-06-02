# Python Rules

**Applies to:** Python service code in `scrapers/` and `muvstok-api/`.

Platform standards: [.agent/standards/coding-standards.md](../standards/coding-standards.md).

## Stack

- Python 3.12+
- FastAPI, Pydantic v2, async I/O where the service already uses it
- `uv` + `ruff` with line length 100
- `mypy` strict in `muvstok-api`

## Structure

- Routes thin -> services -> repositories/clients -> DB, Redis, or external APIs.
- Validate at API boundaries with Pydantic models.
- No shared Python packages between `scrapers/` and `muvstok-api/`.

## Safety

- Never log or commit secrets, tokens, connection strings, or callback HMAC values.
- Preserve `correlation_id`, `job_id`, and `batch_group_id` through logs and callbacks.
- Run service gates before marking work done: `make -C scrapers test lint`, `make check-muvstok`.
