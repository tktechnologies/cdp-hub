# CDP maintenance guide

**Updated:** 2026-06-11. Design: [ARCHITECTURE.md](ARCHITECTURE.md). API/Azure reference: [PLATFORM_OVERVIEW.md](PLATFORM_OVERVIEW.md). Agent tiers: [architecture/AGENT_ARCHITECTURE.md](architecture/AGENT_ARCHITECTURE.md).

## Maintenance starter prompts (copy into an agent chat)

| Type | Prompt |
|------|--------|
| Scraper | [.agent/prompts/maintenance/scraper.md](../.agent/prompts/maintenance/scraper.md) |
| StokAPI / API | [.agent/prompts/maintenance/stokapi.md](../.agent/prompts/maintenance/stokapi.md) |
| n8n workflows | [.agent/prompts/maintenance/n8n.md](../.agent/prompts/maintenance/n8n.md) |
| Infrastructure | [.agent/prompts/maintenance/infrastructure.md](../.agent/prompts/maintenance/infrastructure.md) |
| STOKAI audit / price smoke / cutover prep | [.agent/prompts/maintenance/stokai-audit-cutover.md](../.agent/prompts/maintenance/stokai-audit-cutover.md) |
| `.agent` / docs / agent rules | [.agent/prompts/maintenance/agent-workspace.md](../.agent/prompts/maintenance/agent-workspace.md) |
| Full stack / platform | [.agent/prompts/maintenance/platform-fullstack.md](../.agent/prompts/maintenance/platform-fullstack.md) |

Index: [.agent/prompts/maintenance/README.md](../.agent/prompts/maintenance/README.md).

Cross-service ownership map: [.agent/knowledge/service-catalog.md](../.agent/knowledge/service-catalog.md).

## Scraper cache (24h)

Configured on **scraper API + worker** (not n8n):

```bash
SCRAPE_CACHE_ENABLED=true
SCRAPE_CACHE_TTL_SECONDS=86400
SCRAPE_CACHE_TTL_NOT_FOUND_SECONDS=86400
SCRAPE_CACHE_TTL_BLOCKED_SECONDS=86400
SCRAPE_CACHE_PG_FALLBACK=true
```

Router always sends `force_refresh: false` on `POST /api/v1/jobs`.

| Task | Command / doc |
|------|----------------|
| Local cache smoke | `scrapers/scripts/test_scrape_cache_local.sh` |
| Spec | `scrapers/docs/SPECS/SCRAPE_CACHE_SPEC.md` |
| Operations | `scrapers/docs/SCRAPE_CACHE_OPERATIONS.md` |
| Production audits | `scrapers/docs/validation/` |

## Scraper service

| Task | Path |
|------|------|
| Agent entry | `scrapers/.agent/index.md` |
| Handoff snapshot | `scrapers/docs/MAINTENANCE_CHECKPOINT.md` |
| Local dev | `make -C scrapers setup dev` / `make worker` |
| Tests | `make -C scrapers test lint` |
| Azure deploy | `scripts/deploy-scraper-azure.sh`, `infra/` |

## API Diversos / StokAPI

| Task | Path |
|------|------|
| Agent entry | `muvstok-api/AGENTS.md` → `.agent/` |
| Deploy API | `muvstok-api/scripts/deploy_muv_api.sh` |
| Deploy worker | `muvstok-api/scripts/deploy_muv_worker.sh` |
| Quality gates | `make check-muvstok` or `cd muvstok-api && UV_CACHE_DIR=/tmp/uv-cache uv run ruff check . && UV_CACHE_DIR=/tmp/uv-cache uv run mypy app` |
| Production audit | `muvstok-api/docs/PRODUCTION_AUDIT.md` |

## n8n

| Task | Path |
|------|------|
| Router logic | `n8n/src/*.js` → `make sync-n8n` |
| Scraper receiver | `n8n/workflows/cdp_scraper.json` |
| StokAPI receiver | `n8n/workflows/cdp_stokapi.json` |
| Live IDs | `docs/n8n/LIVE_WORKFLOWS.md` |

**Do not** use deprecated `cdp_muvstok-api_starter` or removed `muvstok_job_*.json` for production dispatch.

## Dual pipeline smoke

```bash
make smoke-cache
```

## Azure (shared)

- Resource group: `automation`
- Key Vault: `cdp-scrapers-kv-prod`
- n8n: `https://automacao.tktechnologies.com.br` (custom hostname bound to `cdp-n8n-prod`)
- Scraper deploy falls back to remote `az acr build --no-logs` when the local Docker daemon is unavailable.

## Azure (STOKAI production target)

- Resource group: `stokai-tk`
- Key Vault: `cdp-stokai-kv-prod`
- ACR: `cdpstokaitkacr`
- Scraper: `cdp-stokai-scrapers-api-prod`, `cdp-stokai-scrapers-worker-prod`
- StokAPI: `cdp-stokai-muv-api`, `cdp-stokai-muv-worker`
- n8n: none in `stokai-tk`; shared n8n uses `STOKAI - cdp_*` workflow copies after cutover.
- Runbook: [runbooks/deploy-stokai.md](runbooks/deploy-stokai.md)
