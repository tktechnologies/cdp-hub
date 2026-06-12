# Maintenance prompt — STOKAI audit, price smoke, and n8n cutover prep

**Tier:** platform + infrastructure + both service APIs

---

## Prompt (copy into chat)

```text
You are the senior maintenance agent for the CDP STOKAI production target.

Mission: audit the CDP-owned services deployed in Azure resource group
`stokai-tk`, run direct SKU smokes that prove real price retrieval, inspect the
STOKAI database, and only then prepare shared n8n to send jobs to the new
workers. Do not cut over n8n router/progress until I explicitly approve it.

Bootstrap (read before acting):
1. AGENTS.md
2. docs/runbooks/deploy-stokai.md
3. .agent/memory/implementation-state.md
4. docs/ENVIRONMENTS.md
5. docs/n8n/LIVE_WORKFLOWS.md
6. docs/ARCHITECTURE.md and docs/PLATFORM_OVERVIEW.md only if you need extra context

Hard boundaries:
- Only inspect or modify CDP-owned resources in `stokai-tk`: resources named
  `cdp-*` plus ACR `cdpstokaitkacr`.
- Do not touch unrelated resources in `stokai-tk`.
- Do not change or delete anything in `automation`; it is backup/rollback.
- Do not deploy n8n into `stokai-tk`.
- Do not activate `STOKAI - cdp_router` or `STOKAI - cdp_progress` until direct
  API price smokes and receiver callback smokes pass and I approve cutover.
- Never print secrets. Read API keys/callback secrets inside shell variables.

Live STOKAI facts from 2026-06-11:
- RG: `stokai-tk`
- ACR: `cdpstokaitkacr`
- KV: `cdp-stokai-kv-prod`
- Postgres: `cdp-stokai-pg-prod`, DB `cdp_scraper`
- Redis: `cdp-stokai-redis-prod`
- Container Apps env: `cdp-stokai-prod-env`
- Scraper API: `cdp-stokai-scrapers-api-prod`
  `https://cdp-stokai-scrapers-api-prod.bluewater-4bfb07b7.eastus2.azurecontainerapps.io`
- Scraper worker: `cdp-stokai-scrapers-worker-prod`
- StokAPI API: `cdp-stokai-muv-api`
  `https://cdp-stokai-muv-api.bluewater-4bfb07b7.eastus2.azurecontainerapps.io`
- StokAPI worker: `cdp-stokai-muv-worker` with ingress disabled
- Images: scraper `cdp-scraper:20260610-2244`, StokAPI API/worker `20260610-2319`
- Last known migration heads: scraper `3c9a6b4e0d12`, StokAPI `20260608_0005`

Work plan:
1. `git status --short`.
2. Audit CDP resources in `stokai-tk`: Container Apps, revisions, ACR images,
   Key Vault secret names, Postgres/Redis presence, and confirm no n8n app.
3. Health-check Scraper and StokAPI public endpoints.
4. Ask me for 3-5 known price-positive SKUs if none are obvious from context.
5. Run direct Scraper tests against STOKAI APIs. Prefer a job or lookup shape
   that proves at least one `FOUND_PRICE` / valid price, not only `not_found`.
6. Run direct StokAPI job tests and poll to terminal status.
7. Inspect STOKAI Postgres with a temporary `cdp-*` firewall rule; remove it
   before final. Report migration heads, table presence, and smoke rows.
8. If direct API price smokes pass, configure or verify shared n8n `CDP_STOKAI_*`
   env vars, then import/sync STOKAI receiver/notifier workflows. Keep
   `STOKAI - cdp_router` and `STOKAI - cdp_progress` inactive.
9. Smoke callback URLs:
   `/webhook/stokai-scraper-result`,
   `/webhook/stokai-muvstok-result`,
   `/webhook/stokai-cdp-notifier`.
10. Stop and summarize. Ask for explicit approval before cutover activation.

Expected final report:
- Resource/revision health table.
- Direct Scraper SKU result with price evidence or exact failure reason.
- Direct StokAPI SKU result with job IDs and DB evidence.
- Database migration/table snapshot.
- n8n readiness status and exact remaining cutover steps.
- Confirmation that temporary firewall rules were removed and no unrelated
  services were changed.
```

## Notes

The first 2026-06-11 STOKAI smoke proved API health, auth, Redis/cache, worker
execution, and DB writes. It did not prove real Scraper price retrieval because
SKU `7703062062` returned `not_found` on GM. The next audit should use
price-positive SKUs before routing production n8n traffic to STOKAI.
