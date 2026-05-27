# Testing Strategy

## Constraint

Official tests run in Azure cloud environments only. The project may include local developer commands, but done/not-done decisions must rely on Azure-hosted validation.

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

## Done Standard

A feature is done only when Azure-hosted tests, quality gates, logs, and required docs pass.
