# Observability

## Required Log Fields

Use structured JSON logs with:

- `timestamp`
- `level`
- `service`
- `environment`
- `correlation_id`
- `job_id`
- `sku`
- `event_name`
- `status`
- `duration_ms`
- `attempt`
- `queue_message_id`
- `worker_id`
- `error_code`
- `error_type`

## Required Events

- API request received and validated.
- Job created and published to Redis.
- Redis message consumed, acknowledged, retried, or dead-lettered.
- Job started and finalized.
- SKU started, succeeded, failed, or retried.
- Token metadata checked and refreshed.
- Raw data saved.
- Governance checks completed.
- Callback started, succeeded, failed, or retried.

## Metrics

Track jobs by lifecycle status, SKUs by outcome, Redis stream depth and pending count, callback attempts and failures, and Muvstok latency and errors.

## Azure

Ship container logs to Azure Monitor and Log Analytics. Use Application Insights and OpenTelemetry when available.
