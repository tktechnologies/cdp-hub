# Testing Playbook

## Constraint

Official tests run in Azure cloud environments only. Local commands can help during development, but done/not-done decisions must rely on Azure-hosted validation.

## Test Layers

- Unit tests run in Azure CI workers.
- Integration tests target Azure-hosted PostgreSQL and Redis test resources.
- Contract tests validate FastAPI OpenAPI behavior in an Azure test deployment.
- End-to-end tests submit jobs, consume Redis messages, persist data, and verify callbacks in Azure.

## Required Coverage

- API key authentication.
- Request validation and idempotency.
- Redis Stream publish, consume, ack, pending, retry, and dead-letter flows.
- Worker restart and resume behavior.
- Muvstok success, timeout, auth failure, token refresh, and server error.
- Large jobs with thousands of SKUs.
- Raw JSONB persistence.
- Callback success, timeout, retry, and permanent failure.
- Security checks for callback URLs and log redaction.

## Local Commands

- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`
- `bash scripts/check_specs.sh`

Use local results as feedback only when Azure validation is required by the task.
