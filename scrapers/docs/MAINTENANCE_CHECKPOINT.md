# Maintenance Checkpoint

**Last updated:** 2026-06-09

**Live snapshot:** [`.agent/memory/implementation-state.md`](../.agent/memory/implementation-state.md) and platform [`.agent/memory/implementation-state.md`](../../.agent/memory/implementation-state.md). Historical site matrix: [`archive/SCRAPER_STATUS_BRIEFING.md`](archive/SCRAPER_STATUS_BRIEFING.md) (2026-05-21).

---

## Production Status

| Area | Status |
|------|--------|
| Azure API + worker | **Live** — verify current image tag in Azure Container Apps |
| Scrapers | Active: `gm`, `ml`, `vw`, `eu`, `melibox`; disabled pending smoke: `pecadireta`; archived: `goparts`, `procurapecas`, `ebay` |
| Proxy | **Applied in production Container Apps** — Key Vault persist still needs Secrets Officer/RBAC |
| Redis scrape cache | **Enabled** — 24h TTL; router sends `force_refresh: false` |
| n8n | **Canonical:** `cdp_router`, `cdp_scraper`, `cdp_stokapi` — [docs/n8n/LIVE_WORKFLOWS.md](../../docs/n8n/LIVE_WORKFLOWS.md) |
| Progress | `cdp_progress` + `dispatch-runs` API — see platform implementation state |

## Production Images

Verify in Azure before deploy (tags below may lag):

| App | Notes |
|-----|--------|
| `cdp-scrapers-api-prod` | Container App in RG `automation` |
| `cdp-scrapers-worker-prod` | Same image tag as API typically |

FQDN: `cdp-scrapers-api-prod.bravecoast-b14d791e.eastus2.azurecontainerapps.io`  
N8N: `https://automacao.tktechnologies.com.br`

---

## Proxy rollout (P0)

| Phase | Action |
|-------|--------|
| A | IPRoyal BR ISP proxies applied to production Container Apps; persist `proxy-urls` in Key Vault when RBAC allows |
| B | `scripts/proxy_readiness_check.py` — Playwright + egress IP before any provider change |
| C | `scripts/proxy_site_smoke.py --from-env` — Melibox first, then Peça Direta/regression sites with `force_refresh` validation |
| D | Restart Container Apps; clear stale `browser_states/` if switching egress |
| E | Re-enable disabled/archived scrapers only after fresh 403-free smoke — see `.agent/workflows/proxy-rollout.md` |

**IPRoyal setup (step-by-step):** [docs/runbooks/iproyal-isp-proxy-setup.md](runbooks/iproyal-isp-proxy-setup.md)  
**Providers (shortlist):** IPRoyal (first test), Decodo, Bright Data (enterprise). Prefer ISP/static BR over Azure datacenter pool.

---

## Agent Quick Start

| Intent | File |
|--------|------|
| **Maintenance prompts (copy into chat)** | `../../.agent/prompts/maintenance/README.md` |
| Scraper maintenance | `../../.agent/prompts/maintenance/scraper.md` |
| Proxy rollout | `.agent/workflows/proxy-rollout.md` |
| Fresh session (short bootstrap) | `.agent/prompts/agent-startup.md` |
| n8n + cache E2E | `.agent/prompts/n8n-cache-integration-test.md` |
| n8n audit | `.agent/skills/n8n-audit/SKILL.md` |
| Publish n8n (user approval only) | `.agent/skills/n8n-release-preflight/SKILL.md` |
| Platform router / sync | `../../.agent/prompts/maintenance/n8n.md` |

---

## Key Scripts

```bash
# Proxy (after purchase)
uv run python scripts/proxy_readiness_check.py --proxy-url 'http://user:pass@host:port'
PROXY_ROTATION_ENABLED=true PROXY_URLS='["http://..."]' \
  uv run python scripts/proxy_site_smoke.py --from-env

# 5-SKU cache audits
uv run python scripts/test_production_5sku_cache_audit.py
uv run python scripts/test_production_5sku_jobs_cache_audit.py

# E2E batch test
./scripts/test_5sku_n8n_e2e.sh

# Production smoke (ML SKU 51766536)
API_BASE_URL=... API_KEY=... uv run python scripts/production_scraper_curl_smoke.py
```

---

## Open Priorities

Top items:

1. Persist `PROXY_URLS` in production Key Vault and run fresh Peça Direta smoke before re-enable
2. ML monitoring uses SKU `51766536` in curl smoke (replacing stale `06K907811B`)
3. Redis TLS validation (`CERT_NONE` → proper)
4. Trim Key Vault webhook secret at source
5. `cdp_progress` live workflow ID on platform
