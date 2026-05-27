# 5-SKU production E2E — 2026-05-21

**Job ID:** `caa95ca5-cd22-48d5-b6de-fa5d038ff90a`  
**Path:** `POST /api/v1/jobs` → Celery worker → callback `cdp_resultado`  
**Sites:** `gm`, `pecadireta`, `melibox`

## Azure scraper — PASS

| SKU | GM | Peça Direta | Melibox | best_price (BRL) |
|-----|-----|-------------|---------|------------------|
| 22781768 | success (cache) | not_found | blocked | 1268.78 |
| 93240598 | success (cache) | success (live) | blocked | 22.64 |
| 793251Y000 | not_found | success (cache) | blocked | 78.784 |
| 53486204 | not_found | success (cache) | blocked | 1.001 |
| 661003M6M00ZZ | not_found | success (live) | blocked (cache) | 99.003 |

- Job status: **completed** (~94s), 5/5 items succeeded
- Worker logs: `Scrape cache hit` for gm/pecadireta/melibox cached rows; live scrapes for cache misses
- Full JSON: `/tmp/5sku_e2e_job.json`

## Worker → n8n callback (automated) — FAIL

```
Callback failed — Illegal header value ... CALLBACK_WEBHOOK_SECRET contains trailing \r
```

Key Vault secret has CR; worker cannot POST until redeploy (`src/config.py` strip) or KV trim.

## n8n receiver — PASS (payload replay)

Manual POST with trimmed secret → execution **361** `success` (1.4s).

- Webhook received `job_id=caa95ca5-...`, all 5 SKU results in body
- `X-Webhook-Secret` verified
- `notify=none` → workflow stops after secret check (no Sheets write in this test)

## Fix

1. Redeploy worker/API with `config.py` credential strip, **or**
2. Trim `callback-webhook-secret` in Key Vault (needs set permission)
