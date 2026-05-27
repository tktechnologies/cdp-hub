# Database Design

## Source Of Truth

PostgreSQL is the durable source of truth for job state, SKU item state, raw Muvstok data, callbacks, errors, audit events, queue messages, and token metadata.

The Muvstok API may share a PostgreSQL database with the scraper API so results can be matched later, but the Muvstok service writes only to Muvstok-owned tables. Cross-service matching should read from both table sets rather than mixing scraper and Muvstok payloads in one table.

Muvstok migrations use the dedicated Alembic version table `muvstok_alembic_version` so they do not conflict with scraper-owned Alembic revisions in the same database.

## Tables

- `api_clients`: clients, key hashes, status, and metadata.
- `muvstok_tokens`: Key Vault secret references and token lifecycle metadata only.
- `muvstok_jobs`: parent job state, callback URL, idempotency key, counts, and metadata.
- `muvstok_job_items`: one row per SKU per job.
- `muvstok_raw_snapshots`: raw Muvstok JSONB responses plus request/response/governance metadata.
- `muvstok_api_data`: one final Muvstok API data row per job item, containing only Muvstok API response payloads and response metadata.
- `callback_attempts`: callback attempts, response codes, errors, and retry state.
- `audit_events`: durable business and security audit trail.
- `ingestion_errors`: normalized error classification for jobs and SKUs.
- `queue_messages`: Redis Stream message references and queue state.

## Large Job Strategy

Jobs with thousands of SKUs are represented as thousands of `muvstok_job_items` rows. Redis messages carry only lightweight job references.

## Index Strategy

- Index `job_id`, `correlation_id`, `status`, and `sku` where used for worker and API lookup paths.
- Unique `(job_id, sku)` prevents duplicate SKU rows per job.
- Unique `muvstok_api_data.job_item_id` keeps one Muvstok API data row per SKU item; retries should update this final-result row while raw attempts remain in `muvstok_raw_snapshots`.
- Unique `(api_client_id, idempotency_key)` supports idempotent submissions when a key is provided.

## Secret Rule

No raw tokens, API keys, passwords, connection strings, or callback HMAC secrets may be stored in plain text.
