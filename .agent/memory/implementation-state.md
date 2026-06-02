# CDP Platform — Implementation State

**Last reviewed:** 2026-06-01 · **Live workflow IDs:** [docs/n8n/LIVE_WORKFLOWS.md](../../docs/n8n/LIVE_WORKFLOWS.md)

## Current snapshot

### n8n (production)

| Workflow | ID | Webhook / trigger | Last known active version |
|----------|-----|-------------------|---------------------------|
| `cdp_router` | `6id6dkinK9xTLfsb` | Telegram, Gmail, schedule | `b56caec9-3b80-4bd1-a756-89919a658ca5` (2026-05-30) |
| `cdp_scraper` | `VfBSV3WU6on8BXm8` | `scraper-result` | `dbb2cd30-cd00-4e67-900b-fadddf9ab770` (2026-05-30) |
| `cdp_stokapi` | `t160mzGPYYlJcrjZ` | `muvstok-result` | see LIVE_WORKFLOWS |
| `cdp_progress` | set `CDP_PROGRESS_WORKFLOW_ID` after first import | Schedule | local JSON only until ID set |

**Sync:** `make sync-n8n` — inject → patch receivers → push JSON via n8n REST API → MCP `publish_workflow`. User approval required.

**Router behavior (2026-05-30):** StokAPI dispatches before scraper branch from `🎲 Limitar SKUs`. Scraper Telegram uses full result evidence, not only `best_price`.

### Scraper (`scrapers/`)

| Item | Value |
|------|--------|
| Stack | FastAPI, Celery, Playwright, PostgreSQL, Redis DB 0/1 |
| Azure | `cdp-scrapers-api-prod`, `cdp-scrapers-worker-prod` |
| Last deploy | 2026-05-27 — `cdpscraperprodacr.azurecr.io/cdp-scraper:latest` |
| Cache | 24h TTL; router `force_refresh: false` |
| Sites | gm, ml, vw, eu, pecadireta (+ melibox via `CDP_SCRAPER_SITES`) |
| Proxy | Code ready; **prod `PROXY_URLS` not confirmed** — rollout: `scrapers/.agent/workflows/proxy-rollout.md` |
| Archived | goparts, procurapecas, ebay — re-enable only after proxy smoke |

### StokAPI (`muvstok-api/`)

| Item | Value |
|------|--------|
| Stack | FastAPI, Redis Streams worker, PostgreSQL |
| Azure | `cdp-muv-api`, `cdp-muv-worker` |
| Last deploy | 2026-05-29 — `cdp-muv-api:20260529-1040`, `cdp-muv-worker:20260529-1040` (duplicate-SKU + per-SKU cache) |
| Branding | API Diversos externally; `muvstok` paths unchanged |

### Shared

- Router/progress Code: `n8n/src/` (13 JS files) → inject via `scripts/sync_workflow_code_from_shared.py`
- Contracts: `contracts/*.schema.json`
- Monorepo root is canonical; nested `.git` removed 2026-05-27

## Known gaps

| Gap | Mitigation |
|-----|------------|
| BR ISP proxy not in prod Key Vault | Buy ISP BR → `proxy_readiness_check.py` → `proxy_site_smoke.py` → Key Vault `proxy-urls` |
| `cdp_progress` needs live workflow ID | Set `CDP_PROGRESS_WORKFLOW_ID` env after first n8n import; then included in `make sync-n8n` |
| GitHub remote not configured | `gh auth login` + add origin when ready |
| Deprecated `scrapers/n8n/docs/` | Stubs point to `docs/n8n/` |

## Changelog (abbreviated)

<details>
<summary>2026-05-27 — 2026-05-30 ops history</summary>

- **2026-05-27:** `make sync-n8n` publish; env access fix on `cdp-n8n-prod`; duplicate SKUs in router DQ; progress APIs + `cdp_progress` JSON.
- **2026-05-29:** Dup-SKU end-to-end (StokAPI cache + N results); row_number sheet writeback via MCP operations; MCP code-based push identified as no-op.
- **2026-05-30:** Router StokAPI-before-scraper dispatch; scraper Telegram evidence-based messages.
- **2026-06-01:** `scripts/n8n_publish.py` — REST API graph push + MCP publish; docs/agent workspace alignment audit.

</details>
