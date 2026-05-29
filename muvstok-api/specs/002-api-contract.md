# API Contract

## Authentication

Protected endpoints use `X-API-Key`. Version 1 may use configured keys while the API client table and key rotation workflow are completed.

## Endpoints

### `POST /api/v1/muvstok/jobs`

Accepts a background ingestion job.

Request:

```json
{
  "skus": ["7703062062", "7701477165"],
  "callback_url": "https://client.example.com/muvstok/callback",
  "metadata": {"source": "erp"},
  "idempotency_key": "optional-client-key"
}
```

Response `202`:

```json
{
  "job_id": "uuid",
  "correlation_id": "uuid",
  "status": "queued",
  "submitted_sku_count": 2,
  "queued_at": "2026-05-03T00:00:00Z"
}
```

### `GET /api/v1/muvstok/jobs/{job_id}`

Returns job state, counts, callback state, and paginated SKU item states.

Query parameters:

- `items_limit`: default `100`, maximum `1000`.
- `items_offset`: default `0`.

### `GET /api/v1/muvstok/health`

Unauthenticated route health check.

## Version 1 Validation

- SKU list must not be empty.
- Duplicate SKUs are **preserved**: a request with N SKUs (including repeats) yields N
  job items and N callback results. The worker fetches each unique SKU once and serves
  duplicates/repeats from cache (in-job memo + Redis 24h), so upstream is not called again.
- Callback URL must be public HTTPS.
- Job size cannot exceed configured `MAX_SKUS_PER_JOB`.
- Reusing the same `idempotency_key` for the same API client returns the existing job.

## Deferred Endpoints

- `POST /api/v1/muvstok`
- `GET /api/v1/muvstok/{id}`
- `POST /api/v1/muvstok/lookup`
- `/metrics` exposure policy
