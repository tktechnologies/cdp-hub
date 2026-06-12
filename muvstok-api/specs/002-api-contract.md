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

### Completion callback

The callback payload posted to `muvstok-result` includes processing counts plus
canonical result counts:

- `found_sku_count`: SKUs with `sku_result = FOUND_PRICE` and
  `has_valid_price = true`.
- `no_price_sku_count`: SKUs found/evidenced without a usable price.
- `not_found_sku_count`: searched SKUs with no match.
- `blocked_sku_count`: upstream/source blocked or access denied.
- `error_sku_count`: parser/request/timeout failures.

Each item/result carries `sku_result`, `source_health`, and `has_valid_price`.
Processing `status = succeeded` means the worker completed the lookup; it is not
a price-found signal unless `sku_result = FOUND_PRICE`.

Receiver sheet output derives seller metadata from raw row aliases:
`vendedor` from branch, `uf` from `uf`/`estado`/state-name/location aliases,
`empresa` from company/legal-name aliases with branch fallback, and `cnpj` as
normalized 14-digit digits. `estado` is not a canonical output field.
The worker enriches missing `uf`/`empresa`/`cnpj` data from the dealership
directory before persistence and callback. It loads `company_locations` from
Postgres first and may fall back to the configured directory CSV when enabled.
It first matches `codigoFilial` to `Lista empresas.id_empresa`; if the upstream
row omits that id, it falls back to exact normalized branch/seller names that
are unique in the directory.

### `GET /api/v1/muvstok/health`

Unauthenticated route health check.

## Version 1 Validation

- SKU list must not be empty.
- Duplicate SKUs are **preserved**: a request with N SKUs (including repeats) yields N
  job items and N callback results. The worker fetches each unique SKU once and serves
  duplicates/repeats from cache (in-job memo + Redis 24h), so upstream is not called again.
- Result semantics are explicit: `FOUND_PRICE`, `NO_PRICE`, `NOT_FOUND`,
  `BLOCKED`, `TIMEOUT`, `ERROR`, and `NOT_QUERIED` are distinct and must not be
  collapsed into worker processing status.
- Callback URL must be public HTTPS.
- Job size cannot exceed configured `MAX_SKUS_PER_JOB`.
- Reusing the same `idempotency_key` for the same API client returns the existing job.

## Deferred Endpoints

- `POST /api/v1/muvstok`
- `GET /api/v1/muvstok/{id}`
- `POST /api/v1/muvstok/lookup`
- `/metrics` exposure policy
