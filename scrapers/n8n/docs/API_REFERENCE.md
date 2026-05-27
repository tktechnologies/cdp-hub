# Scraper API Reference For N8N

> **Service API truth:** `scrapers/src/models/schemas.py` and [contracts/](../../../contracts/). This file may lag; prefer OpenAPI at `/docs` when running locally.

Last updated: 2026-05-27

Base production URL from latest smoke artifact:

```text
https://cdp-scrapers-api-prod.bravecoast-b14d791e.eastus2.azurecontainerapps.io
```

Use the custom/current URL if the production DNS changes. The API exposes
OpenAPI docs at `/docs` when accessible.

## Authentication

All business endpoints require the API key header:

```text
X-API-Key: <API_KEY>
```

The health endpoint does not require authentication.

N8N callback receivers must verify this callback header:

```text
X-Webhook-Secret: <CALLBACK_WEBHOOK_SECRET>
```

The scraper sends that header when it POSTs final job results to
`callback_url`.

## Active Site IDs

Use these values in `sites`:

| Site ID | Source | Production role |
|---|---|---|
| `gm` | GM / Chevrolet parts portal | Active |
| `ml` | Mercado Livre | Active, noisy marketplace |
| `vw` | Volkswagen parts portal | Active |
| `eu` | FastParts export / EU imports | Active, USD/EUR possible |
| `pecadireta` | Peca Direta | Active |
| `melibox` | Melibox Sellerbox portal | Active but production currently blocked at login entry |

Archived site IDs still exist in code and schemas, but should not be used in
new production N8N workflows unless the scraper registry is intentionally
reopened:

```text
goparts, procurapecas, ebay
```

## GET /api/v1/health

Purpose: Check that the API container is running.

Auth: none.

N8N use: run before dispatching batches or in a monitoring workflow.

Example:

```bash
curl https://cdp-scrapers-api-prod.bravecoast-b14d791e.eastus2.azurecontainerapps.io/api/v1/health
```

Response:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "sites": [],
  "active_jobs": 0,
  "uptime_seconds": 0.0
}
```

## POST /api/v1/jobs

Purpose: Submit an asynchronous scraping job. This is the primary endpoint for
N8N.

Auth: `X-API-Key`.

Body:

```json
{
  "items": [
    {
      "sku": "22781768",
      "brand": "GM",
      "description": "Optional human description"
    }
  ],
  "sites": ["gm", "vw", "eu", "pecadireta"],
  "callback_url": "https://automacao.tktechnologies.com.br/webhook/scraper-result",
  "priority": 5
}
```

Fields:

| Field | Required | Rules |
|---|---:|---|
| `items` | Yes | Array of 1 to 500 SKU objects. |
| `items[].sku` | Yes | Part code to search. Trim blanks before sending. |
| `items[].brand` | No | Useful for source-specific rules. Empty string allowed. |
| `items[].description` | No | Carried into persistence for context. |
| `sites` | No | Defaults to active sites: `gm`, `ml`, `vw`, `eu`, `pecadireta`, `melibox`. |
| `callback_url` | No | Production N8N webhook URL for final result delivery. |
| `priority` | No | Integer 1-10. Current default is 5. |

Do not depend on unsupported request fields such as `job_metadata`. The current
API callback payload is built from the typed job/result contract. N8N requester
context should be carried in `callback_url` query parameters or stored in an
external tracking table keyed by `job_id`.

Response:

```json
{
  "job_id": "uuid",
  "status": "pending",
  "total_items": 1,
  "sites": ["gm", "vw", "eu", "pecadireta"],
  "created_at": "2026-05-14T01:00:00Z",
  "estimated_duration_seconds": 60
}
```

N8N rule: after this response, do not wait in the dispatcher workflow. Store or
log the `job_id`, then let the receiver webhook handle final results.

## GET /api/v1/jobs/{job_id}

Purpose: Poll or retrieve durable job status and results from PostgreSQL.

Auth: `X-API-Key`.

Response shape:

```json
{
  "job_id": "uuid",
  "status": "completed",
  "results": [
    {
      "sku": "22781768",
      "brand": "GM",
      "site_results": [
        {
          "site": "gm",
          "site_name": "Chevrolet Parts (pecachevrolet.com.br)",
          "status": "success",
          "error_message": "",
          "results": [
            {
              "sku_searched": "22781768",
              "sku_found": "22781768",
              "exact_match": true,
              "site": "gm",
              "site_name": "Chevrolet Parts (pecachevrolet.com.br)",
              "price": 1015.89,
              "currency": "BRL",
              "condition": "new",
              "availability": "Disponivel",
              "seller_name": "Dealer name",
              "product_url": "https://example.com/product",
              "origin": "Brasil",
              "scraped_at": "2026-05-14T01:29:21.420434Z",
              "raw_title": "Original source title"
            }
          ],
          "search_time_ms": 21104
        }
      ],
      "best_price": {
        "sku_searched": "22781768",
        "sku_found": "22781768",
        "exact_match": true,
        "site": "gm",
        "site_name": "Chevrolet Parts (pecachevrolet.com.br)",
        "price": 1015.89,
        "currency": "BRL",
        "condition": "new",
        "availability": "Disponivel",
        "seller_name": "Dealer name",
        "product_url": "https://example.com/product",
        "origin": "Brasil",
        "scraped_at": "2026-05-14T01:29:21.420434Z",
        "raw_title": "Original source title"
      },
      "total_results": 3
    }
  ],
  "started_at": "2026-05-14T01:00:03Z",
  "completed_at": "2026-05-14T01:01:10Z",
  "duration_seconds": 67.2,
  "total_items": 1,
  "items_succeeded": 1,
  "items_failed": 0,
  "items_processed": 1,
  "progress_pct": 100.0,
  "estimated_seconds_remaining": null,
  "errors": []
}
```

While a job is `running`, `items_processed` and `progress_pct` update incrementally;
`estimated_seconds_remaining` is derived from elapsed time per item when available.

Possible job statuses:

```text
pending, running, completed, failed, partial
```

## POST /api/v1/dispatch-runs

Purpose: Register or refresh an active dual-pipeline dispatch run (written by
`cdp_router` after Scraper + StokAPI jobs are accepted).

Auth: `X-API-Key`.

Body:

```json
{
  "batch_group_id": "uuid-or-sheet-batch-id",
  "chat_id": "telegram-chat-id",
  "command_route": ".analisar",
  "total_skus": 42,
  "scraper_job_ids": ["job-uuid-1", "job-uuid-2"],
  "stokapi_job_id": "stok-job-uuid",
  "estimated_seconds": 3600
}
```

Response: `DispatchRunResponse` with `id`, job IDs, `total_skus`, progress
notification fields (`last_progress_pct`, `progress_message_count`, …).

## GET /api/v1/dispatch-runs/active

Purpose: List dispatch runs that have not completed. Used by `cdp_progress`
schedule workflow.

Auth: `X-API-Key`.

Response: array of `DispatchRunResponse`.

## GET /api/v1/dispatch-runs/active/for-chat/{chat_id}

Purpose: Latest active dispatch run for a Telegram chat. Used by `.status`
when workflow staticData is empty.

Auth: `X-API-Key`.

Returns `404` when no active run exists for the chat.

## PATCH /api/v1/dispatch-runs/{run_id}

Purpose: Update progress notification state after a proactive Telegram message.

Auth: `X-API-Key`.

Body (all fields optional):

```json
{
  "last_progress_pct": 40,
  "progress_message_count": 2,
  "scraper_status": "running",
  "stokapi_status": "processing"
}
```

## POST /api/v1/lookup

Purpose: Synchronous single-SKU lookup.

Auth: `X-API-Key`.

Body:

```json
{
  "sku": "22781768",
  "brand": "GM",
  "sites": ["gm"],
  "force_refresh": false
}
```

Response: one `SKUResult` with per-site `from_cache` / `cached_at` and summary
`cache_hits` / `live_scrapes`. By default each site is served from Redis when a
snapshot exists within the TTL window (24h for priced hits); set
`force_refresh: true` to bypass cache.

`POST /api/v1/jobs` accepts the same `force_refresh` flag on the job body.

N8N rule: use only for manual tests, smoke checks, and very small interactive
flows. It waits up to 120 seconds and can return `408 Lookup timed out`.
Batch production flows should use `/jobs` (also cache-aware).

## POST /api/v1/demo/interview

Purpose: Local demo endpoint that starts the same headed browser tour as
`make interview-demo` in the API process background.

Auth: `X-API-Key`.

Body:

```json
{
  "chat_id": "local-demo",
  "sites": "gm,ml,vw",
  "timeout_seconds": 180,
  "headless": false
}
```

Response:

```json
{
  "demo_id": "uuid",
  "status": "running",
  "telegram_chat_id": "local-demo",
  "status_url": "/api/v1/demo/interview/uuid"
}
```

N8N rule: use this endpoint for local demos only. Poll the returned
`status_url`; do not use it for production batch scraping.

## GET /api/v1/demo/interview/{demo_id}

Purpose: Poll a local interview demo started by `POST /demo/interview`.

Auth: `X-API-Key`.

Terminal statuses:

```text
completed, failed
```

When completed, `summary_text` contains the short human-readable demo recap.

## HTTP Errors N8N Should Handle

| Status | Meaning | N8N action |
|---:|---|---|
| 401 | Invalid or missing API key | Stop workflow and alert; do not retry blindly. |
| 404 | Unknown job ID or no result for lookup | Mark as missing or invalid job reference. |
| 408 | Synchronous lookup timed out | Switch to `/jobs` + callback. |
| 500 | Unexpected API error | Retry once for transient issues, then alert with payload and job ID. |
