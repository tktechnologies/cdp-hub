# CDP Platform — Implementation State

**Last reviewed:** 2026-06-02 · **Live workflow IDs:** [docs/n8n/LIVE_WORKFLOWS.md](../../docs/n8n/LIVE_WORKFLOWS.md)

## Current snapshot

### n8n (production)

| Workflow | ID | Webhook / trigger | Last known active version |
|----------|-----|-------------------|---------------------------|
| `cdp_router` | `6id6dkinK9xTLfsb` | Telegram, Gmail, schedule | `9a312497-3c02-49f6-857c-dfd176a176fc` (2026-06-02) |
| `cdp_scraper` | `VfBSV3WU6on8BXm8` | `scraper-result` | `acdfd664-3d85-4341-a28c-fe03b2a2afb5` (2026-06-02) |
| `cdp_stokapi` | `t160mzGPYYlJcrjZ` | `muvstok-result` | `fdfa6140-a735-4442-8c4f-899109967c5d` (2026-06-02) |
| `cdp_progress` | `V9I6o32XDoPIRarz` | Schedule | active via REST (2026-06-02) |

**Sync:** `make sync-n8n` — inject → patch receivers → REST PUT (`scripts/n8n_publish.py`) → MCP `publish_workflow`. Set `CDP_PROGRESS_WORKFLOW_ID=V9I6o32XDoPIRarz` (or export before sync) to include progress.

**GitHub:** `origin` and `tktech` → `cdp-hub` `main` @ `ba177cb+` (monorepo sync 2026-06-02).

### Scraper (`scrapers/`)

| Item | Value |
|------|--------|
| Stack | FastAPI, Celery, Playwright, PostgreSQL, Redis DB 0/1 |
| Azure prod | `cdp-scrapers-api-prod`, `cdp-scrapers-worker-prod` |
| Last deploy | 2026-06-02 — `cdpscraperprodacr.azurecr.io/cdp-scraper:20260602-2102` |
| Azure dev | `cdp-scrapers-api-dev`, `cdp-scrapers-worker-dev` (provision via `scrapers/scripts/deploy-azure-dev.sh`) |
| Cache | 24h TTL; router `force_refresh: false` |
| Sites | gm, ml, vw, eu, pecadireta (+ melibox via `CDP_SCRAPER_SITES`) |
| Proxy | Code ready; **prod `PROXY_URLS` not confirmed** — rollout: `scrapers/.agent/workflows/proxy-rollout.md` |

### StokAPI (`muvstok-api/`)

| Item | Value |
|------|--------|
| Stack | FastAPI, Redis Streams worker, PostgreSQL |
| Azure prod | `cdp-muv-api`, `cdp-muv-worker` |
| Last deploy | 2026-05-29 — `cdp-muv-api:20260529-1040` (unchanged 2026-06-02; no app diff) |
| Azure dev | `cdp-muv-api-dev`, `cdp-muv-worker-dev` (scripts ready; apps after dev KV/infra) |

### Shared

- Router/progress Code: `n8n/src/` → inject via `scripts/sync_workflow_code_from_shared.py`
- Contracts: `contracts/*.schema.json`
- Environments: [ADR-0006](../../docs/decisions/ADR-0006-dev-production-environments.md)

## Known gaps

| Gap | Mitigation |
|-----|------------|
| BR ISP proxy not in prod Key Vault | Buy ISP BR → `proxy_readiness_check.py` → `proxy_site_smoke.py` → Key Vault `proxy-urls` |
| `N8N_API_KEY` in `~/.cursor/mcp.json` | Use `muvstok-api/.env` or export `N8N_API_KEY` before `make sync-n8n` |
| StokAPI dev Container Apps | Provision after dev scraper stack + `deploy_muv_dev.sh` |
| Deprecated `scrapers/n8n/docs/` | Stubs point to `docs/n8n/` |

## Changelog (abbreviated)

<details>
<summary>2026-05-27 — 2026-06-02 ops history</summary>

- **2026-06-02:** Full platform sync — GitHub push, n8n publish (router/scraper/stokapi/progress), scraper image `20260602-2102`, dev stack deploy script + ADR-0006, `n8n_publish.py` settings sanitizer.
- **2026-06-01:** Agent workspace audit; `scripts/n8n_publish.py` REST + MCP publish.
- **2026-05-30:** Router StokAPI-before-scraper; scraper Telegram evidence-based messages.
- **2026-05-29:** Dup-SKU end-to-end (StokAPI cache + N results).

</details>
