# Maintenance Checkpoint

**Last updated:** 2026-05-27

**Live snapshot:** Prefer [`.agent/memory/implementation-state.md`](../.agent/memory/implementation-state.md) and platform [`.agent/memory/implementation-state.md`](../../.agent/memory/implementation-state.md) for workflow IDs. Verify Azure image tags before deploy.

---

## Production Status

| Area | Status |
|------|--------|
| Azure API + worker | **Live** — verify current image tag in Azure Container Apps |
| Scrapers | Active sites: `gm`, `ml`, `vw`, `eu`, `pecadireta`; `melibox` optional |
| Redis scrape cache | **Enabled** — 24h TTL; router sends `force_refresh: false` |
| n8n | **Canonical:** `cdp_router`, `cdp_scraper`, `cdp_stokapi` — see [docs/n8n/LIVE_WORKFLOWS.md](../../docs/n8n/LIVE_WORKFLOWS.md) |
| Progress | `cdp_progress` + `dispatch-runs` API — import workflow; see platform implementation state |

## Production Images

Verify in Azure before deploy (tags below may lag):

| App | Notes |
|-----|--------|
| `cdp-scrapers-api-prod` | Container App in RG `automation` |
| `cdp-scrapers-worker-prod` | Same image tag as API typically |

FQDN: `cdp-scrapers-api-prod.bravecoast-b14d791e.eastus2.azurecontainerapps.io`  
N8N: `https://automacao.tktechnologies.com.br`

---

## Agent Quick Start

| Intent | File |
|--------|------|
| **Maintenance prompts (copy into chat)** | `../../.agent/prompts/maintenance/README.md` |
| Scraper maintenance | `../../.agent/prompts/maintenance/scraper.md` |
| Fresh session (short bootstrap) | `.agent/prompts/agent-startup.md` |
| n8n + cache E2E | `.agent/prompts/n8n-cache-integration-test.md` |
| n8n audit | `.agent/skills/n8n-audit/SKILL.md` |
| Publish n8n (user approval only) | `.agent/skills/n8n-release-preflight/SKILL.md` |
| Platform router / sync | `../../.agent/prompts/maintenance/n8n.md` |

---

## Key Scripts

```bash
# 5-SKU cache audits
uv run python scripts/test_production_5sku_cache_audit.py
uv run python scripts/test_production_5sku_jobs_cache_audit.py

# E2E batch test
./scripts/test_5sku_n8n_e2e.sh

# Production smoke
API_BASE_URL=... API_KEY=... uv run python scripts/production_scraper_curl_smoke.py
```

---

## Open Priorities

See `docs/TASKS.md`. Top items:
1. ML positive smoke SKU / Melibox 403
2. Redis TLS validation (`CERT_NONE` → proper)
3. Proxy URLs or disable rotation in prod
4. Trim Key Vault webhook secret at source
