# Observability (Platform)

## Structured logging

Use structured JSON logs with correlation across API, queue, worker, and callbacks:

- `correlation_id`, `job_id`, `batch_group_id` where applicable
- `event_name`, `status`, `duration_ms`, `attempt`
- Redact secrets, tokens, and `X-Webhook-Secret` values

## Required lifecycle events

| Layer | Events |
|-------|--------|
| API | Request validated, job created, dispatch-run registered |
| Queue | Enqueued, consumed, acked, retried, dead-lettered |
| Worker | SKU/site started, succeeded, failed, job terminal |
| Callback | Attempt started, HTTP status, failure classification |

## Progress (dual pipeline)

- Scraper: `items_processed`, `progress_pct`, `estimated_seconds_remaining` on `GET /api/v1/jobs/{id}`
- StokAPI: live item counts on `GET /api/v1/muvstok/jobs/{id}`
- Router: `.status` / `cdp_progress` poll these + `GET /api/v1/dispatch-runs/active`

## Azure

- Container Apps → Log Analytics / Azure Monitor
- Application Insights / OpenTelemetry when enabled in service deploy configs

Service detail: `muvstok-api/.agent/standards/observability.md`, scraper logging in `scrapers/src/`.
