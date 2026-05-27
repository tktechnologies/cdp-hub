# N8N Workflow Builder Guide

> **Deprecated.** Canonical guide: [docs/n8n/WORKFLOW_GUIDE.md](../../../docs/n8n/WORKFLOW_GUIDE.md). Workflow names: `cdp_router`, `cdp_scraper` (not `cdp_analise` / `cdp_resultado`).

Last updated: 2026-05-19

Use this guide when building importable N8N JSON workflows for the scraper.

## Recommended Workflow Architecture

Use two separate workflows:

```text
Workflow A: Job Dispatcher
  Trigger -> Read SKUs -> Normalize/Batch -> POST /api/v1/jobs -> Record job_id

Workflow B: Result Receiver
  Webhook -> Verify X-Webhook-Secret -> Flatten Results -> Store/Notify
```

This prevents N8N HTTP timeouts because scraping can take minutes per batch.
The current live receiver webhook responds immediately, then continues sheet and
notification work inside N8N. That is acceptable because the scraper API only
needs to know that the callback was accepted.

## Production Workflows Only

This repo maintains only the two production CDP workflows (`cdp_analise`,
`cdp_resultado`). Local demo workflows have been removed to keep the repo focused.

## Workflow A: Dispatcher

Expected nodes:

| Node | Purpose |
|---|---|
| Manual Trigger or Schedule Trigger | Starts the dispatcher. Add Schedule if workflow must be active. |
| Source node | Reads SKUs from Google Sheets, webhook input, form input, database, or another API. |
| Code node | Maps input columns to API fields, removes blanks, deduplicates, and batches. |
| HTTP Request | `POST /api/v1/jobs` with `X-API-Key`. |
| IF or Code check | Confirms response status is `pending`. |
| Log/store node | Saves `job_id`, batch metadata, and source row references. |

Input column mapping commonly used by operations:

| Source column | API field |
|---|---|
| `CODIGO` | `sku` |
| `ITEM` | `description` |
| `UNIDADE` | `brand` |

Dispatcher Code node pattern:

```javascript
const API_SITES = ['gm', 'ml', 'vw', 'eu', 'pecadireta'];
const CALLBACK_URL = 'https://automacao.tktechnologies.com.br/webhook/scraper-result';
const BATCH_SIZE = 25;

const rows = $input.all();
const seen = new Set();

const items = rows
  .map((item) => {
    const row = item.json;
    const sku = String(row.CODIGO ?? row.sku ?? '').trim();
    return {
      sku,
      brand: String(row.UNIDADE ?? row.brand ?? '').trim(),
      description: String(row.ITEM ?? row.description ?? '').trim(),
    };
  })
  .filter((item) => item.sku.length > 0)
  .filter((item) => {
    const key = `${item.sku}|${item.brand}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

const batches = [];
for (let i = 0; i < items.length; i += BATCH_SIZE) {
  batches.push(items.slice(i, i + BATCH_SIZE));
}

return batches.map((batch) => ({
  json: {
    items: batch,
    sites: API_SITES,
    callback_url: CALLBACK_URL,
    priority: 5,
  },
}));
```

If the workflow needs batch metadata, store it in a separate tracking sheet or
data store keyed by the returned `job_id`. Keep the API body limited to
documented fields.

HTTP Request node:

| Setting | Value |
|---|---|
| Method | `POST` |
| URL | `https://cdp-scrapers-api-prod.bravecoast-b14d791e.eastus2.azurecontainerapps.io/api/v1/jobs` |
| Headers | `Content-Type: application/json`, `X-API-Key: <API_KEY>` |
| Body type | JSON |
| Body | `items`, `sites`, `callback_url`, `priority` |
| Timeout | Short, for example 30 seconds. Do not wait for scraping here. |

Do not put requester routing metadata in the API body. The current scraper API
does not persist arbitrary `job_metadata` into callback payloads. Put requester
context in `callback_url` query parameters instead, for example `notify`,
`chat_id`, `reply_email`, and `ad_hoc`.

## Workflow B: Receiver

Expected nodes:

| Node | Purpose |
|---|---|
| Webhook Trigger | Receives `POST /webhook/scraper-result`. |
| IF or Code verifier | Validates `X-Webhook-Secret`. |
| Code node | Flattens nested job results. |
| Destination node | Google Sheets, Airtable, database, Slack, email, or downstream API. |
| Optional Respond to Webhook | Only needed if the webhook is configured to wait for a response node. The live CDP receiver responds immediately. |

Webhook settings:

| Setting | Value |
|---|---|
| HTTP Method | `POST` |
| Path | `scraper-result` |
| Response mode | Immediate response in the live workflow. Use response node only for short, synchronous test workflows. |
| Production URL | `https://automacao.tktechnologies.com.br/webhook/scraper-result` |
| Test URL | Use only when N8N is listening for a test event. |

Secret verification:
- Check the request header `x-webhook-secret`.
- Compare to `CALLBACK_WEBHOOK_SECRET`.
- Reject with HTTP `401` when invalid.

Flatten Code node pattern:

```javascript
const payload = $json.body ?? $json;
const rows = [];

for (const skuResult of payload.results ?? []) {
  const best = skuResult.best_price;

  for (const siteResult of skuResult.site_results ?? []) {
    const parts = siteResult.results ?? [];

    if (parts.length === 0) {
      rows.push({
        json: {
          job_id: payload.job_id,
          job_status: payload.status,
          sku: skuResult.sku,
          brand: skuResult.brand ?? '',
          site: siteResult.site,
          site_name: siteResult.site_name,
          site_status: siteResult.status,
          site_error_message: siteResult.error_message ?? '',
          sku_searched: skuResult.sku,
          sku_found: '',
          exact_match: false,
          price: '',
          currency: '',
          condition: '',
          availability: siteResult.status,
          seller_name: '',
          product_url: '',
          origin: '',
          raw_title: String(siteResult.status ?? '').toUpperCase(),
          scraped_at: '',
          search_time_ms: siteResult.search_time_ms ?? 0,
          is_best_price: false,
          job_started_at: payload.started_at ?? '',
          job_completed_at: payload.completed_at ?? '',
          job_duration_seconds: payload.duration_seconds ?? '',
        },
      });
      continue;
    }

    for (const part of parts) {
      const isBest = Boolean(
        best &&
        part.site === best.site &&
        part.sku_found === best.sku_found &&
        part.price === best.price &&
        part.product_url === best.product_url
      );

      rows.push({
        json: {
          job_id: payload.job_id,
          job_status: payload.status,
          sku: skuResult.sku,
          brand: skuResult.brand ?? '',
          site: siteResult.site,
          site_name: siteResult.site_name,
          site_status: siteResult.status,
          site_error_message: siteResult.error_message ?? '',
          sku_searched: part.sku_searched,
          sku_found: part.sku_found,
          exact_match: part.exact_match,
          price: part.price ?? '',
          currency: part.currency ?? '',
          condition: part.condition ?? '',
          availability: part.availability ?? '',
          seller_name: part.seller_name ?? '',
          product_url: part.product_url ?? '',
          origin: part.origin ?? '',
          raw_title: part.raw_title ?? '',
          scraped_at: part.scraped_at ?? '',
          search_time_ms: siteResult.search_time_ms ?? 0,
          is_best_price: isBest,
          job_started_at: payload.started_at ?? '',
          job_completed_at: payload.completed_at ?? '',
          job_duration_seconds: payload.duration_seconds ?? '',
        },
      });
    }
  }
}

return rows;
```

If using a response node for a small test workflow, success body:

```json
{
  "status": "received",
  "message": "Results processed successfully"
}
```

## Site Selection Practices

Default active set for broad production jobs:

```javascript
['gm', 'ml', 'vw', 'eu', 'pecadireta']
```

Add `melibox` only when the workflow owner accepts that production may return
`blocked` until the current access issue is resolved.

Do not include archived sites in new production workflows unless explicitly
requested:

```javascript
['goparts', 'procurapecas', 'ebay']
```

## Batching Practices

The API allows up to 500 items per job. N8N should still prefer smaller batches
for operational clarity.

Recommended starting points:

| Job type | Batch size |
|---|---:|
| Manual test | 1-3 SKUs |
| Daily production with several sites | 10-25 SKUs |
| Single stable source only | 25-100 SKUs |
| Debugging a source issue | 1 SKU and 1 site |

## Testing Checklist

1. Check API health:

```text
GET /api/v1/health
```

2. Test receiver workflow with a sample callback before dispatching real jobs.
3. Dispatch one SKU to one stable site, such as `gm` with SKU `22781768`.
4. Confirm dispatcher records `job_id`.
5. Confirm receiver flattens final callback rows.
6. Confirm `blocked`, `timeout`, `error`, `not_found`, and `no_price` remain
   distinguishable in output.

## Common Agent Mistakes To Avoid

| Mistake | Correct practice |
|---|---|
| Using `/lookup` for batch workflows | Use `/jobs` plus receiver webhook. |
| Including archived site IDs by habit | Use active site IDs only. |
| Treating `blocked` as `not_found` | Keep source health statuses distinct. |
| Calculating best price across currencies | Convert currencies first or leave comparison null. |
| Dropping site results with empty `results` | Write placeholder audit rows. |
| Waiting in dispatcher for final scrape result | End dispatcher after `pending`; receiver handles completion. |
| Sending extra metadata in API body | Keep API payload to documented fields. Store metadata elsewhere. |
