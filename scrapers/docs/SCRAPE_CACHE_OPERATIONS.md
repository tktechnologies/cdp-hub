# Scrape Cache Operations

Runbook for the 24-hour per-site SKU Redis cache. Source of truth for behavior:
`docs/SPECS/SCRAPE_CACHE_SPEC.md`.

## Prerequisites

| Layer | Local | Azure production |
|-------|-------|------------------|
| Redis | `docker compose up -d redis` — cache uses **DB 1** | Same Azure Redis as Celery, **DB 1** (`/1` in URL) |
| API | `make dev` or `docker compose up` | `cdp-scrapers-api-prod` |
| Worker | optional locally (`JOB_EXECUTION_BACKEND=local`) | `cdp-scrapers-worker-prod` (required for `/jobs`) |
| Env | `.env` from `.env.example` | Container App secrets via Bicep / Key Vault |

## Local test (quick)

```bash
# 1. Stack
docker compose up -d postgres redis
cp .env.example .env   # ensure SCRAPE_CACHE_ENABLED=true

# 2. API
make dev

# 3. Automated smoke (two lookups + force_refresh)
chmod +x scripts/test_scrape_cache_local.sh
API_KEY=dev-key-change-in-production ./scripts/test_scrape_cache_local.sh
```

Manual curl:

```bash
# Live scrape
curl -s -X POST http://localhost:8000/api/v1/lookup \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"sku":"93338835","brand":"GM","sites":["gm"],"force_refresh":true}' \
  | jq '{cache_hits, live_scrapes, from_cache: .site_results[0].from_cache}'

# Cache hit (repeat within 24h)
curl -s -X POST http://localhost:8000/api/v1/lookup \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"sku":"93338835","brand":"GM","sites":["gm"]}' \
  | jq '{cache_hits, live_scrapes, from_cache: .site_results[0].from_cache}'
```

Inspect Redis:

```bash
redis-cli -n 1 KEYS 'scrape:v1:*'
redis-cli -n 1 TTL 'scrape:v1:gm:_:93338835'
```

## Unit tests (no Redis)

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests/test_services/test_scrape_cache.py -v
```

## Azure deploy

After merging cache code, redeploy image and ensure Container Apps have cache env vars
(see `infra/modules/container-app.bicep`):

- `SCRAPE_CACHE_ENABLED=true`
- `SCRAPE_CACHE_REDIS_URL` → `rediss://...:6380/1` (secret)
- `SCRAPE_SITES_SEQUENTIAL=true` (default: one live site at a time)

```bash
# Rebuild + deploy (existing flow)
IMAGE_TAG=scrape-cache-$(date +%Y%m%d-%H%M) ../../scripts/deploy-scraper-azure.sh
```

Or update only Container App env without full rebuild if image already contains cache code.

## Azure production test

```bash
API_FQDN="$(az containerapp show -g automation -n cdp-scrapers-api-prod \
  --query properties.configuration.ingress.fqdn -o tsv | tr -d '\r\n')"
API_KEY="$(az keyvault secret show --vault-name cdp-scrapers-kv-prod \
  --name api-key --query value -o tsv | tr -d '\r\n')"

chmod +x scripts/test_scrape_cache_production.sh
API_BASE="https://${API_FQDN}/api/v1" API_KEY="${API_KEY}" \
  ./scripts/test_scrape_cache_production.sh

# 5-SKU live + cache audit — random sample from production_sku_pool (~27 SKUs)
uv run python scripts/test_production_5sku_cache_audit.py
# Reproducible draw: uv run python scripts/test_production_5sku_cache_audit.py --seed 42
# Or: PRODUCTION_TEST_SKU_SEED=42 uv run python scripts/test_production_5sku_jobs_cache_audit.py
```

Single-SKU curl example:

```bash
curl -s -X POST "${API_BASE}/lookup" \
  -H "X-API-Key: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"sku":"22781768","brand":"GM","sites":["gm"],"force_refresh":false}' \
  | jq '{cache_hits, live_scrapes, from_cache: .site_results[0].from_cache, best_price}'
```

Expected on **second** lookup: `from_cache=true`, `cache_hits >= 1`, `live_scrapes=0`.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Always `live_scrapes` = all sites | `SCRAPE_CACHE_ENABLED=false` or Redis down (logs: "Redis unavailable"); on Azure use DB 1 (`rediss://...:6380/1`) and let the app configure TLS |
| `Invalid API key` from smoke script | Trim CR/LF from Key Vault / `az` output (`tr -d '\r\n'`) before curl |
| Cache never hits after first call | Wrong Redis DB (must be `/1`), or API/worker using different URLs |
| Stale blocked or not_found status cached 24h | Expected anti-bot behavior; use `force_refresh=true` only for an intentional manual recheck |
| `/jobs` not cached | Worker must have same `SCRAPE_CACHE_*` env as API |

## Agent prompt

Fresh agent sessions: read `.agent/prompts/agent-startup.md` then `docs/SPECS/SCRAPE_CACHE_SPEC.md`.

## n8n `cdp_router`

The router always posts jobs with `force_refresh: false`. Repeat `.analisar` / `.sku` for the same SKU/site within 24h is served from **Redis (86400s)** or PostgreSQL warm fallback — no extra n8n dedup layer.

Platform doc: `cdp-app/docs/architecture/DUAL_ANALISE.md` (or `docs/CDP_PLATFORM.md`).
