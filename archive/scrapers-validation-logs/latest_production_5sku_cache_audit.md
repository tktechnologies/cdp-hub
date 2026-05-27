# Production 5-SKU cache audit

**Date:** 2026-05-21  
**API image:** `cdpscraperprodacr.azurecr.io/cdp-scraper:lookup-direct-20260521-1439`  
**Result:** **5/5 PASS**

| Case | SKU | Site | Live (ms) | Cached (ms) | Cached status |
|------|-----|------|-----------|-------------|---------------|
| gm-22781768 | 22781768 | gm | 12053 | 2425 | success, `from_cache=true` |
| gm-93240598 | 93240598 | gm | 6044 | 2414 | success, `from_cache=true` |
| pecadireta-793251 | 793251Y000 | pecadireta | 4434 | 2421 | success, `from_cache=true` |
| pecadireta-53486204 | 53486204 | pecadireta | 3516 | 2422 | success, `from_cache=true` |
| melibox-661003 | 661003M6M00ZZ | melibox | 7148 | 2425 | blocked (cached 30m TTL), `from_cache=true` |

All cached calls: `cache_hits=1`, `live_scrapes=0`.

Full JSON: `latest_production_5sku_cache_audit.json`
