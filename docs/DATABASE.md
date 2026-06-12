# CDP platform — database and cache

**Updated:** 2026-05-27

PostgreSQL is the durable source of truth for job state, scrape results, and Muvstok ingestion. Redis provides queues, hot scrape cache, and (for StokAPI) job dispatch streams. The two services may share one PostgreSQL instance but use **separate Alembic version tables** and **non-overlapping table ownership**.

| Service | Alembic path | Version table | Owned tables |
|---------|--------------|---------------|--------------|
| Scraper | `scrapers/alembic/` | `alembic_version` | `scrape_*`, `dispatch_runs`, `session_states`, `part_results` |
| StokAPI | `muvstok-api/app/db/migrations/` | `muvstok_alembic_version` | `muvstok_*`, `api_clients`, `queue_messages`, … |

Run migrations from each service directory (`alembic upgrade head` / service Makefile). No destructive schema changes without an explicit migration plan.

---

## PostgreSQL — Scraper (`scrapers/`)

### Tables

| Table | Purpose |
|-------|---------|
| `scrape_jobs` | Batch scrape jobs: status, sites, counters, callback URL, timing, optional `metadata` JSON |
| `scrape_items` | One row per SKU in a job; `site_results` JSON snapshots per site |
| `part_results` | Normalized part rows linked to `scrape_items` (audit / PG cache warm path) |
| `dispatch_runs` | Dual-pipeline run registry (scraper + StokAPI job IDs, progress, chat binding) |
| `session_states` | Per-site Playwright session health |

### Indexes (query paths)

| Index | Columns | Use |
|-------|---------|-----|
| `ix_scrape_jobs_status_created_at` | `(status, created_at)` | List/filter jobs by status and recency |
| `ix_dispatch_runs_chat_id` | `(chat_id)` | `GET /dispatch-runs/active/for-chat/{chat_id}` |
| `ix_dispatch_runs_batch_group_id` | `(batch_group_id)` | Upsert by batch group |
| `ix_scrape_items_sku` | `(sku)` | PG scrape-cache fallback by SKU |
| `ix_part_results_sku_searched` | `(sku_searched)` | Historical part lookups |

ORM: `scrapers/src/models/database.py`. Migrations: `scrapers/alembic/versions/`.

### Future: `price_history` (optional)

Not implemented. A dedicated time-series table (e.g. `price_history`: `sku`, `site`, `price`, `currency`, `observed_at`, `job_id`, `source`) would support trend charts and sheet “Histórico” without scanning `part_results`. Until then, use `part_results.scraped_at` and latest job rows for point-in-time prices. Add via a new Alembic revision when product requires it.

---

## PostgreSQL — StokAPI (`muvstok-api/`)

### Tables

| Table | Purpose |
|-------|---------|
| `muvstok_jobs` | Parent job: status, counts, callback, idempotency |
| `muvstok_job_items` | One row per SKU per job |
| `muvstok_raw_snapshots` | Raw Muvstok JSONB per attempt |
| `muvstok_api_data` | Final normalized payload per job item |
| `callback_attempts`, `audit_events`, `ingestion_errors`, `queue_messages` | Ops and queue bookkeeping |
| `api_clients`, `muvstok_tokens` | Auth and token metadata (secrets in Key Vault only) |

### Indexes (query paths)

| Index | Columns | Use |
|-------|---------|-----|
| `ix_muvstok_jobs_status` | `(status)` | Status-only filters |
| `ix_muvstok_jobs_status_created_at` | `(status, created_at)` | Status + ordering |
| `ix_muvstok_jobs_correlation_id` | `(correlation_id)` | Trace by correlation |
| `ix_muvstok_job_items_status_job_id` | `(status, job_id)` | Worker item progress |
| `uq_muvstok_job_items_job_sku` | `(job_id, sku)` | Dedup per job |

ORM: `muvstok-api/app/db/models.py`. Design notes: `muvstok-api/specs/004-database-design.md`.

---

## Redis layout

Single Azure Redis instance is typical; **logical DB index** separates concerns.

| DB | Env (Scraper) | Env (StokAPI) | Purpose |
|----|---------------|---------------|---------|
| **0** | `REDIS_URL` | `REDIS_URL` | Celery broker/result (Scraper); Redis Streams job queue (StokAPI) |
| **1** | `SCRAPE_CACHE_REDIS_URL` | — | Scrape result hot cache only |

StokAPI does not use DB 1 today.

### Key naming

| Prefix / key | Service | TTL | Notes |
|--------------|---------|-----|-------|
| `scrape:v1:{site}:{brand_key}:{sku_key}` | Scraper | 24h for success/no_price/not_found/blocked | JSON `SiteResult` payload; see `scrapers/src/redis_keys.py` |
| `dispatch:run:{run_id}` | Scraper | *reserved* | Constants only; `dispatch_runs` table is authoritative |
| `progress:{chat_id}` or `progress:{run_id}` | Platform | *reserved* | Ephemeral n8n/Telegram poll state; not written in production yet |
| `muvstok:jobs` | StokAPI | Stream (no key TTL) | `XADD` job payloads; consumer group `muvstok-workers` |
| `muvstok:jobs:dead-letter` | StokAPI | Stream | Failed messages after retries |

Celery also creates broker keys on DB 0 (`celery-task-meta-*`, etc.) — do not share DB 0 with scrape cache.

### Scrape cache TTL strategy

| Site status | Cached | Default TTL (`SCRAPE_CACHE_*`) |
|-------------|--------|--------------------------------|
| `success`, `no_price` | Yes | `SCRAPE_CACHE_TTL_SECONDS` (86400) |
| `not_found` | Yes | `SCRAPE_CACHE_TTL_NOT_FOUND_SECONDS` (86400) |
| `blocked` | Yes | `SCRAPE_CACHE_TTL_BLOCKED_SECONDS` (86400) |
| `error`, `timeout` | No | Listed in `SCRAPE_CACHE_BYPASS_STATUSES` |

On Redis miss, optional PostgreSQL warm path (`SCRAPE_CACHE_PG_FALLBACK`) repopulates Redis from recent `scrape_items` / `part_results` within the success TTL window.

Details: `scrapers/docs/SPECS/SCRAPE_CACHE_SPEC.md`, `scrapers/docs/SCRAPE_CACHE_OPERATIONS.md`.

---

## Observability

Scraper Prometheus (`GET /metrics`):

| Metric | Labels | Meaning |
|--------|--------|---------|
| `cdp_scrape_cache_hit_total` | `source` (`redis`, `postgresql`) | Cache served without live scrape |
| `cdp_scrape_cache_miss_total` | — | No cache entry; caller may live-scrape |
| `cdp_scrape_requests_total` | `site`, `status` | Live scrape outcomes |
| `cdp_scrape_duration_seconds` | `site` | Live scrape latency |

---

## Related docs

- [PLATFORM_OVERVIEW.md](PLATFORM_OVERVIEW.md)
- [architecture/DUAL_PIPELINE.md](architecture/DUAL_PIPELINE.md)
- `scrapers/docs/SYSTEM_OVERVIEW.md`
- `muvstok-api/specs/004-database-design.md`
