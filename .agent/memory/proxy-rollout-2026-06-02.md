# Proxy rollout plan applied — 2026-06-02

## Code and docs delivered

- `scrapers/scripts/proxy_site_smoke.py` — per-site SKU smoke with `--from-env`
- `scrapers/.agent/workflows/proxy-rollout.md` — phased checklist
- `scrapers/AGENTS.md`, `MAINTENANCE_CHECKPOINT.md`, implementation-state (service + platform)
- ML curl smoke SKU → `51766536`
- Historical banner on `SCRAPER_STATUS_BRIEFING.md`

## Still requires human / purchase

1. Buy Brazilian ISP/static residential proxy (IPRoyal, Decodo, or Bright Data).
2. Store JSON array in Key Vault `proxy-urls`; restart Container Apps.
3. Run `proxy_readiness_check.py` then `proxy_site_smoke.py --from-env`.
4. Re-enable archived scrapers only if smoke passes per site.

## Not done (by design)

- No production Key Vault secret values committed
- No `SCRAPER_REGISTRY` changes for goparts/procurapecas until smoke evidence
- No `make sync-n8n` (user approval required)
