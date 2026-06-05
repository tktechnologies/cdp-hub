# Glossary

- API client: external system submitting Muvstok ingestion jobs.
- Callback: outbound HTTP request sent when job results or status are ready.
- Correlation ID: request/job identifier propagated through logs, database rows, queue messages, and callbacks.
- Dead-letter stream: Redis Stream for poison jobs that cannot complete after retries.
- Idempotency key: optional client-provided key used to return an existing job for duplicate submissions.
- Job: parent ingestion request containing one or more SKUs.
- Key Vault reference: database-safe pointer to a secret stored in Azure Key Vault.
- Muvstok: upstream service queried for SKU data.
- Queue message: lightweight Redis Stream record carrying job identifiers, not the full SKU list.
- SKU item: one SKU within a job, tracked independently in PostgreSQL.
- SKU result: business/search outcome for one SKU, separate from processing
  lifecycle. Values: `FOUND_PRICE`, `NO_PRICE`, `NOT_FOUND`, `BLOCKED`,
  `TIMEOUT`, `ERROR`, `NOT_QUERIED`.
- Source health: source availability/quality outcome for one lookup. Values:
  `OK`/`WORKING`, `BLOCKED`, `TIMEOUT`, `ERROR`, `NOT_QUERIED`.
- Valid price: positive usable sale price. `has_valid_price=true` is required
  for found-price reporting.
- Snapshot: raw Muvstok JSONB response and related request/response metadata.
- Worker: background process that consumes Redis job messages and processes SKUs.
