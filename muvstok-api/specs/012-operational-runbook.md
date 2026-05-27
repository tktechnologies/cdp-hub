# Operational Runbook

## Azure Validation

Official validation happens in Azure cloud environments. Capture logs, traces, test reports, and database assertions from Azure resources.

## Common Operations

- Submit a job with `POST /api/v1/muvstok/jobs`.
- Inspect job state with `GET /api/v1/muvstok/jobs/{job_id}`.
- Inspect Redis stream depth and pending entries.
- Inspect failed jobs in PostgreSQL.
- Replay resumable jobs by publishing a new lightweight Redis message.
- Inspect callback failures in `callback_attempts`.
- Rotate Muvstok secrets in Azure Key Vault.
- Review logs by `correlation_id` and `job_id`.

## Recovery Principles

- PostgreSQL state decides what work remains.
- Redis messages can be recreated from durable job state.
- Callback failures can be retried without refetching all Muvstok data.
