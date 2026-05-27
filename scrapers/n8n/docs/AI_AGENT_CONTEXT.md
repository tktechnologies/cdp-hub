# AI Agent Context For CDP Scraper N8N Workflows

> **Deprecated for agents.** Use [scrapers/.agent/skills/n8n-audit/SKILL.md](../../.agent/skills/n8n-audit/SKILL.md) and [docs/n8n/WORKFLOW_GUIDE.md](../../../docs/n8n/WORKFLOW_GUIDE.md).

Last updated: 2026-05-22

You are building or editing N8N workflows for the CDP automotive parts scraper.
Read this before generating workflow JSON.

## Mission

Create reliable N8N automation that submits automotive SKU scraping jobs,
receives completed results, preserves source status honestly, and stores or
routes normalized quote data.

## API Boundary

Use the scraper API. Do not query production PostgreSQL directly from normal
workflows.

Production API base:

```text
https://cdp-scrapers-api-prod.bravecoast-b14d791e.eastus2.azurecontainerapps.io
```

Primary endpoint:

```text
POST /api/v1/jobs
```

Headers:

```text
Content-Type: application/json
X-API-Key: <API_KEY>
```

Callback auth sent by the scraper:

```text
X-Webhook-Secret: <CALLBACK_WEBHOOK_SECRET>
```

## Correct Workflow Shape

Use two workflows:

```text
Dispatcher:
  read SKUs -> transform/batch -> POST /api/v1/jobs -> save job_id

Receiver:
  webhook -> verify x-webhook-secret -> flatten results -> store/notify
```

Avoid `/api/v1/lookup` for production batches because it waits for completion
and can time out.

Live workflow IDs:

```text
cdp_router: 6id6dkinK9xTLfsb
cdp_scraper: VfBSV3WU6on8BXm8
cdp_stokapi: t160mzGPYYlJcrjZ
```

## Dual dispatch (`.analisar` and `.sku`)

On `cdp_router`:

1. Save requester (`cdp_sheet_requester` staticData).
2. Read SKUs (sheet or ad-hoc), DQ, **5-SKU sample** (`🎲 Limitar SKUs`).
3. **Parallel:** POST scraper `/api/v1/jobs` (per SKU, sites not scraped today) + POST StokAPI `/api/v1/muvstok/jobs`.
4. Two completion notifications via `cdp_scraper` and `cdp_stokapi`.

Publish from monorepo root: `make sync-n8n`. Router Code sources: `cdp-app/n8n/src/`.

## Valid Active Sites

Use:

```text
gm, ml, vw, eu, pecadireta
```

Optional with known current risk:

```text
melibox
```

Do not use archived sites unless explicitly instructed:

```text
goparts, procurapecas, ebay
```

## Job Payload

```json
{
  "items": [
    {
      "sku": "22781768",
      "brand": "GM",
      "description": "optional"
    }
  ],
  "sites": ["gm", "vw"],
  "callback_url": "https://automacao.tktechnologies.com.br/webhook/scraper-result",
  "priority": 5
}
```

Only send documented fields. If you need batch metadata, save it in N8N storage,
a sheet, or another tracking system using the returned `job_id`.

Requester notification context must travel in `callback_url` query parameters
because the current API callback does not include arbitrary `job_metadata`.

## Result Semantics

`exact_match` is critical. A nice price without exact SKU evidence is diagnostic
data, not a reliable quote.

Keep these statuses distinct:

```text
success, not_found, no_price, blocked, timeout, error
```

Do not treat `blocked`, `timeout`, or `error` as part unavailability.

`best_price` exists only when there is at least one positive exact-match price
and all priced exact matches use the same currency.

Do not compare BRL, USD, and EUR without an explicit conversion step.

## Infrastructure Facts

Production resources:

```text
API: cdp-scrapers-api-prod
Worker: cdp-scrapers-worker-prod
N8N: cdp-n8n-prod
PostgreSQL: cdp-scrapers-pg-prod
Redis: cdp-scrapers-redis-prod
Key Vault: cdp-scrapers-kv-prod
ACR: cdpscraperprodacr
Resource group: automation
```

The worker uses Celery through Redis. Jobs are durable in PostgreSQL.

Current production snapshot from 2026-05-14:
- API and N8N health passed.
- `gm`, `vw`, `eu`, `pecadireta` passed smoke checks.
- `ml` returned `not_found` for an old smoke SKU.
- `melibox` returned `blocked` due to `403 forbidden` at login entry.

## Output Rows

When flattening, emit one row per product result. For a site with no product
results, emit one placeholder row so operations can see that the site was
checked.

Recommended key columns:

```text
job_id, job_status, sku, brand, site, site_status, sku_searched, sku_found,
exact_match, price, currency, condition, availability, seller_name,
product_url, origin, raw_title, scraped_at, search_time_ms, is_best_price
```

## Quality Bar

Before finishing a workflow:
- Validate API key header is present.
- Verify receiver checks `x-webhook-secret`.
- Test receiver with sample payload.
- Test dispatcher with one SKU and one site.
- Make sure archived sites are not accidentally included.
- Make sure the workflow does not collapse `blocked`, `timeout`, `error`, and
  `not_found` into one value.
