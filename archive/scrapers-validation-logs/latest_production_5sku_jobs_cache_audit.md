# Production 5-SKU /jobs cache audit

**Date:** 2026-05-21  
**Worker image:** `scrape-cache-ssl-20260521-1402`  
**Result:** **5/5 cache PASS** (worker `/jobs` path)

| Case | SKU | Site | Job1 cache | Job2 cache | Job status | best_price |
|------|-----|------|------------|------------|------------|------------|
| gm-22781768 | 22781768 | gm | hits=1 live=0 | hits=1 live=0 | completed | BRL 1268.78 exact |
| gm-93240598 | 93240598 | gm | hits=1 live=0 | hits=1 live=0 | completed | BRL 22.64 exact |
| pecadireta-793251 | 793251Y000 | pecadireta | hits=1 live=0 | hits=1 live=0 | completed | BRL 78.784 exact |
| pecadireta-53486204 | 53486204 | pecadireta | hits=1 live=0 | hits=1 live=0 | completed | BRL 1.001 exact |
| melibox-661003 | 661003M6M00ZZ | melibox | hits=1 live=0 | hits=1 live=0 | failed (blocked) | — |

All site rows: `from_cache=true`. Melibox job `failed` at job level but correctly caches `blocked` (30m TTL).

## Callback E2E (Phase 3)

Jobs with `callback_url` (first 3 SKUs): **callbacks failed** in worker logs:

```text
Illegal header value ... CALLBACK_WEBHOOK_SECRET contains trailing \\r
```

Manual webhook probe with trimmed Key Vault secret → n8n execution **354 success**.

**Fix:** `src/config.py` now strips `\r\n` from `callback_webhook_secret` and `api_key` on load. Redeploy worker (or trim Key Vault secret) for production callbacks.

Full JSON: `latest_production_5sku_jobs_cache_audit.json`
