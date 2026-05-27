# 5-SKU production E2E — post A27 deploy (2026-05-21)

**Job ID:** `86f8b3a4-b661-4183-b4ab-558f79dfa0de`  
**Seed:** `42` (reproducible via `PRODUCTION_TEST_SKU_SEED=42`)  
**Images:** `cdpscraperprodacr.azurecr.io/cdp-scraper:callback-strip-20260521-1649` (API + worker)  
**Path:** `POST /api/v1/jobs` → Celery worker → callback `cdp_resultado`

## Azure scraper — PASS (partial)

| SKU | GM | Peça Direta | Melibox | best_price (BRL) |
|-----|-----|-------------|---------|------------------|
| 868857LR8A | not_found | not_found | blocked | — |
| 06K907811B | not_found | success | blocked | 4523.44 |
| 22781768 | success | not_found | blocked | 1268.78 |
| C1BB/ 15A222/DA/5YZ | not_found | no_price | blocked | 154.60 |
| 767203M6M01 | not_found | no_price | blocked | 266.73 |

- Job status: **partial** (~52s), 4/5 items succeeded, 1 failed (melibox re-auth noise; cached blocked)
- All sites served from cache (`cache_hits=3`, `live_scrapes=0` per SKU)
- Full JSON: `docs/validation/latest_5sku_e2e_post_a27.json`

## Worker → n8n callback (automated) — PASS

```
HTTP Request: POST .../webhook/scraper-result?source=5sku-e2e&notify=none "HTTP/1.1 200 OK"
Callback sent — job_id=86f8b3a4-b661-4183-b4ab-558f79dfa0de status_code=200
```

Credential strip in `src/config.py` deployed; no trailing `\r` header error.

## n8n receiver — PASS

- Execution **369** `success` (webhook, ~1.5s), aligned with callback timestamp `19:54:45Z`
- Prior automated callback from debug job `b18307f0-...`: execution **368** `success`

## Script fix

`scripts/test_5sku_n8n_e2e.sh` — SKU listing printed to stdout corrupted JSON body (422). Fixed by sending display lines to stderr.
