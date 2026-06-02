# StokAPI n8n — Workflow Guide

**Updated:** 2026-05-26

## Production model (CDP dual pipeline)

| Component | Workflow | ID | Role |
|-----------|----------|-----|------|
| **Dispatch** | `cdp_router` | `6id6dkinK9xTLfsb` | Inline `POST /api/v1/muvstok/jobs` via `n8n/src/router_stokapi.js` |
| **Receiver** | `cdp_stokapi` | `t160mzGPYYlJcrjZ` | Webhook `muvstok-result` → Sheets + Telegram |

```text
cdp_router (.analisar / .sku)
  → POST {CDP_MUVSTOK_API_BASE}/api/v1/muvstok/jobs
  → Redis Stream → cdp-muv-worker → PostgreSQL
  → POST callback …/webhook/muvstok-result
  → cdp_stokapi
```

**Deprecated:** `cdp_muvstok-api_starter` (`PXLHDzRbBVgs8Xl2`), removed `muvstok_job_sender.json` / `muvstok_job_receiver.json`. Do not use Execute Workflow from router for StokAPI.

Platform docs: `cdp-app/docs/PLATFORM_OVERVIEW.md`, `cdp-app/docs/architecture/DUAL_PIPELINE.md`.

## Sync from repo

```bash
cd /path/to/cdp-app
make sync-n8n
```

Receiver JSON: `n8n/workflows/cdp_stokapi.json` (monorepo root).

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| CDP Muvstok API | Container App `cdp-muv-api`. Health: `GET /api/v1/muvstok/health`. |
| Worker | `cdp-muv-worker` must process Redis Stream `muvstok:jobs`. |
| n8n env vars | See `n8n/settings/cdp_stokapi.json` `required_env`. |
| Google Sheets | Shared CDP sheets (see below). |
| Telegram | Bot credential in n8n. |

## Environment variables (n8n container)

Production (`cdp-n8n-prod`, RG `automation`): secrets in Key Vault `cdp-scrapers-kv-prod`.

| Key Vault secret | n8n env var(s) |
|------------------|----------------|
| `api-key` | `CDP_API_KEY`, `CDP_MUVSTOK_API_KEY` |
| `callback-webhook-secret` | `CDP_CALLBACK_WEBHOOK_SECRET`, `CDP_MUVSTOK_CALLBACK_WEBHOOK_SECRET` |
| `cdp-muvstok-api-base` | `CDP_MUVSTOK_API_BASE` |

Plain env: `WEBHOOK_URL`, `CDP_MUVSTOK_WEBHOOK_PATH=webhook/muvstok-result`.

| Variable | Example | Purpose |
|----------|---------|---------|
| `CDP_MUVSTOK_API_BASE` | `https://cdp-muv-api.….azurecontainerapps.io` | API base (no trailing slash). |
| `CDP_MUVSTOK_API_KEY` | *(secret)* | `X-API-Key` for job creation (router uses this). |
| `WEBHOOK_URL` | `https://automacao.tktechnologies.com.br` | n8n public base. |
| `CDP_MUVSTOK_CALLBACK_WEBHOOK_SECRET` | *(secret)* | Must match API `CALLBACK_WEBHOOK_SECRET`. |

## Router dispatch (cdp_router)

Implemented in `cdp-app/n8n/src/router_stokapi.js`:

- Runs for `.analisar` and `.sku` when valid SKUs exist (all valid SKUs by default; optional `CDP_DISPATCH_SAMPLE_SIZE` in router).
- Builds `callback_url` → `webhook/muvstok-result` with query: `notify`, `batch_group_id`, `dual_run=stokapi`, `command_route`, optional `chat_id` / `reply_email`.
- POST body to `{CDP_MUVSTOK_API_BASE}/api/v1/muvstok/jobs`.
- Metadata: `source: cdp_router`, `pipeline: stokapi`, `batch_group_id`.
- Idempotency: `{batchGroupId}-stokapi-1`.

### Job request (`202`)

```json
{
  "skus": ["7703062062"],
  "callback_url": "https://automacao.example.com/webhook/muvstok-result?notify=telegram&batch_group_id=bg-…&dual_run=stokapi",
  "metadata": { "source": "cdp_router", "pipeline": "stokapi" },
  "idempotency_key": "bg-…-stokapi-1"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `skus` | yes | Non-empty string array. |
| `callback_url` | yes | Public HTTPS n8n webhook URL. |
| `metadata` | no | Stored on job. |
| `idempotency_key` | no | Reuse returns same job. |

## Receiver: `cdp_stokapi`

**File:** `n8n/workflows/cdp_stokapi.json`

### Webhook

| Setting | Value |
|---------|--------|
| Method | `POST` |
| Path | `muvstok-result` |
| Production URL | `{WEBHOOK_URL}/webhook/muvstok-result` |

### Security

Compare header `x-webhook-secret` to `CDP_MUVSTOK_CALLBACK_WEBHOOK_SECRET` (or `CALLBACK_WEBHOOK_SECRET`). Reject with 401 when invalid.

### Callback payload

Aligned with `app/schemas/callbacks.py`:

```json
{
  "job_id": "uuid",
  "correlation_id": "uuid",
  "status": "succeeded",
  "submitted_sku_count": 10,
  "succeeded_sku_count": 8,
  "failed_sku_count": 2,
  "items": [
    { "sku": "661003M6M00ZZ", "status": "succeeded", "snapshot_id": "uuid" }
  ],
  "metadata": { "source": "cdp_router" },
  "completed_at": "2026-05-21T12:05:00Z"
}
```

Extended payloads may include `results[]` with warehouse rows. The flatten node supports both shapes.

### Flow

1. Webhook — receive callback.
2. Verify secret.
3. Extrair linhas — one sheet row per listing (or placeholder per failed SKU).
4. Append to results sheet (`cdp_resultados`).
5. Update `cdp_skus` — `PROCESSADO`, `ENCONTRADO`.
6. Telegram summary when `chat_id` present.

## Google Sheets (production)

### Source — SKU intake (`cdp_skus`)

| | |
|---|---|
| Document ID | `1IGhsIhrwlnMaCduR-W-eIi9O4mMO2pPYjE-tefgIPII` |
| Tab | **SKUs** |

| Column | Router / receiver |
|--------|-------------------|
| `CODIGO` | SKU key |
| `PROCESSADO` | `processando...` on dispatch; `processado` on callback |
| `ENCONTRADO` | `✅ Encontrado` / `✗ Não encontrado` |

### Delivery — results (`cdp_resultados`)

Document ID: `1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo`

Tabs: **Detalhado** (per listing), **Historico** (per job), **Resumo** (best price per SKU).

Column mapping and price rules: see `docs/MUVSTOK_SHEETS_AUDIT.md`.

**Detalhado:** `site` = `API Diversos`, `preco` = `valorPrecoVenda`, `preco-medio` = `valorCustoMedio`, `melibox_tipo` = stock code `0`–`4`, `vendedor` = branch, `url_produto` = empty.  
**Resumo:** `MELHOR PREÇO` = lowest sale price (`valorPrecoVenda`); `LINK` = empty.

## Deployment checklist

1. Set n8n env vars on `cdp-n8n-prod`.
2. Sync and activate **cdp_stokapi** (receiver must be live before callbacks).
3. Deploy `cdp-muv-api` with `deploy_muv_api.sh` and worker with `deploy_muv_worker.sh`.
4. Sync **cdp_router** from monorepo (`make sync-n8n`).
5. Run `.sku TESTSKU` via Telegram; confirm sheet + Telegram from receiver.

## Related docs

- `specs/002-api-contract.md` — job API
- `../../docs/n8n/LIVE_WORKFLOWS.md` — live IDs
- `../../scrapers/n8n/docs/N8N_WORKFLOW_GUIDE.md` — scraper receiver patterns (service docs)
- `../../n8n/workflows/cdp_scraper.json` — scraper receiver JSON (monorepo root)
- `docs/MUVSTOK_SHEETS_AUDIT.md` — sheet column audit
