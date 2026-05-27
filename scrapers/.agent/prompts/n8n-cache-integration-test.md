# N8N + Cache Integration Test

Run this prompt to validate the full pipeline: scraper API → cache → worker → n8n callback.

## Prerequisites

- Azure CLI logged in (`az account show`)
- n8n MCP server enabled

## Phase 1 — n8n Audit

1. MCP `search_workflows` query `cdp` → verify `cdp_router`, `cdp_scraper`, and `cdp_stokapi` active.
2. Compare live vs monorepo `n8n/workflows/*.json` (dispatcher sites, body fields, receiver auth).
3. Fix drift in repo exports if found. Do NOT publish unless user says "publish".

## Phase 2 — Scraper + Cache Tests

Use 5 random SKUs from `scripts/production_sku_pool.py`:

```bash
uv run python scripts/test_production_5sku_cache_audit.py
uv run python scripts/test_production_5sku_jobs_cache_audit.py
```

PASS: second /jobs call shows `cache_hits >= 1`, `live_scrapes = 0`.

## Phase 3 — E2E

```bash
./scripts/test_5sku_n8n_e2e.sh
```

Verify receiver webhook execution succeeds and rows match delivery contract.

## PASS Criteria

- API + worker health OK
- No critical n8n contract drift
- ≥4/5 SKUs cache hit on second /jobs
- Receiver callback → execution success

## Report

End with: `n8n PASS/FAIL — Cache PASS/FAIL — E2E PASS/FAIL — next: ...`
