# Scrape Result Cache Spec

## Purpose

Reduce live Playwright traffic and anti-bot risk by caching per-site SKU scrape
results in Redis for a configurable TTL (default 24 hours). PostgreSQL remains
the audit trail; Redis is the fast path.

## Flow

```text
SKU request (lookup or job)
  → for each requested site:
      → Redis GET (key: site + brand + normalized SKU)
      → on miss: optional PostgreSQL fallback (latest row within TTL window)
      → on still miss: live scrape → SET Redis + persist job rows as today
  → assemble SKUResult (cache_hits / live_scrapes counts)
```

## Redis Keys

- Prefix: `scrape:v1:`
- Key: `scrape:v1:{site}:{brand_key}:{sku_key}`
- `sku_key`: uppercase alphanumeric after stripping spaces, `-`, `.`, `/`
- `brand_key`: lowercase stripped brand or `_`
- Database index: **1** by default (`SCRAPE_CACHE_REDIS_URL=redis://localhost:6379/1`)
  so Celery broker keys on DB 0 stay isolated.

## TTL Policy

| Site status | Cached | Default TTL |
|-------------|--------|-------------|
| `success` | Yes | 86400 s (24h) |
| `no_price` | Yes | 86400 s |
| `not_found` | Yes | 21600 s (6h) |
| `blocked` | Short | 1800 s (30m) |
| `error`, `timeout` | No | — |

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `SCRAPE_CACHE_ENABLED` | `true` | Master switch |
| `SCRAPE_CACHE_REDIS_URL` | `redis://localhost:6379/1` | Cache Redis URL |
| `SCRAPE_CACHE_TTL_SECONDS` | `86400` | success / no_price TTL |
| `SCRAPE_CACHE_TTL_NOT_FOUND_SECONDS` | `21600` | not_found TTL |
| `SCRAPE_CACHE_TTL_BLOCKED_SECONDS` | `1800` | blocked TTL |
| `SCRAPE_CACHE_PG_FALLBACK` | `true` | Warm Redis from PostgreSQL on miss |
| `SCRAPE_CACHE_BYPASS_STATUSES` | `error,timeout` | Never write cache |
| `SCRAPE_SITES_SEQUENTIAL` | `false` | Live scrapes per SKU run up to 3 sites in parallel |

## API

- `force_refresh` on `ScrapeJobRequest` and `SingleSKURequest` skips cache reads.
- `SiteResult.from_cache` and `SiteResult.cached_at` indicate cache origin.
- `SKUResult.cache_hits` / `live_scrapes` summarize the path taken.

## Operations

- Local: `docker compose up -d redis` before enabling cache.
- Production: set `SCRAPE_CACHE_REDIS_URL` to the same Azure Redis instance on **DB 1**
  (or a dedicated cache DB). Restart API and worker after env change.

## Metrics

Prometheus counters on `GET /metrics`:

- `cdp_scrape_cache_hit_total{source="redis|postgresql"}`
- `cdp_scrape_cache_miss_total`

## Future

- Cache stampede lock per `(site, sku)`
- Admin `DELETE /api/v1/cache/{sku}` endpoint
