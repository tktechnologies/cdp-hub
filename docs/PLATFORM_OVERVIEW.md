# CDP Platform — API & Azure reference

**Updated:** 2026-06-11

This file is the **deep reference** for endpoints, router Code files, progress env vars, and Azure names. For layout, dual pipeline, and agent tiers, read [ARCHITECTURE.md](ARCHITECTURE.md) first.

| Topic | Canonical doc |
|-------|----------------|
| System design | [ARCHITECTURE.md](ARCHITECTURE.md) |
| `.analisar` / cache / duplicates | [architecture/DUAL_PIPELINE.md](architecture/DUAL_PIPELINE.md) |
| Live workflow IDs + publish | [n8n/LIVE_WORKFLOWS.md](n8n/LIVE_WORKFLOWS.md) |
| Agent tiers | [architecture/AGENT_ARCHITECTURE.md](architecture/AGENT_ARCHITECTURE.md) |
| ADRs | [decisions/README.md](decisions/README.md) |

## Services (Azure)

| Service | Directory | Azure apps |
|---------|-----------|------------|
| Scraper (`automation`) | `scrapers/` | `cdp-scrapers-api-prod`, `cdp-scrapers-worker-prod` |
| StokAPI (`automation`) | `muvstok-api/` | `cdp-muv-api`, `cdp-muv-worker` |
| Scraper (`stokai-tk`) | `scrapers/` | `cdp-stokai-scrapers-api-prod`, `cdp-stokai-scrapers-worker-prod` |
| StokAPI (`stokai-tk`) | `muvstok-api/` | `cdp-stokai-muv-api`, `cdp-stokai-muv-worker` |
| n8n | `n8n/` | `cdp-n8n-prod` → `https://automacao.tktechnologies.com.br` |
| Dev (scraper) | `scrapers/` | `cdp-scrapers-api-dev`, `cdp-scrapers-worker-dev`, KV `cdp-scrapers-kv-dev` |

Shared/backup prod: RG `automation`, Key Vault `cdp-scrapers-kv-prod`, ACR
`cdpscraperprodacr.azurecr.io`. STOKAI prod target: RG `stokai-tk`, Key Vault
`cdp-stokai-kv-prod`, ACR `cdpstokaitkacr.azurecr.io`. Dev/prod split:
[decisions/ADR-0006-dev-production-environments.md](decisions/ADR-0006-dev-production-environments.md).
Database/Redis: [DATABASE.md](DATABASE.md). STOKAI deploy/runbook:
[runbooks/deploy-stokai.md](runbooks/deploy-stokai.md).

## n8n workflow IDs

See [n8n/LIVE_WORKFLOWS.md](n8n/LIVE_WORKFLOWS.md) — do not duplicate IDs here.

## Router Code (`n8n/src/`)

| File | Role |
|------|------|
| `router_limitar_skus.js` | Batch metadata; all valid SKUs (optional `CDP_DISPATCH_SAMPLE_SIZE`) |
| `formatar_payload_scraper.js` | Scraper job bodies |
| `router_stokapi.js` | StokAPI job bodies |
| `emparelhar_scraper.js` | Mark sheet PROCESSADO |
| `router_error_stokapi.js` | StokAPI dispatch errors |
| `router_register_run.js` | Active run + `POST /dispatch-runs` |
| `router_status_prepare.js` / `router_status.js` | `.status` / `.andamento` / `.progresso` |
| `progress_poll.js` / `progress_format.js` | `cdp_progress` schedule workflow |

After edits: `python3 scripts/sync_workflow_code_from_shared.py` → `make sync-n8n` (user approval).

## Progress env (n8n)

| Variable | Default | Meaning |
|----------|---------|---------|
| `CDP_PROGRESS_INTERVAL_MIN` | `10` | Schedule interval (`0` = off) |
| `CDP_PROGRESS_MIN_SKUS` | `15` | Min SKUs before proactive notify |
| `CDP_PROGRESS_MIN_STEP_PCT` | `10` | Min % step between messages |
| `CDP_PROGRESS_MAX_MESSAGES` | `6` | Cap per run |

## API quick reference

### Scraper (`scrapers/`)

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/api/v1/jobs` | Async batch |
| `GET` | `/api/v1/jobs/{id}` | Status + `progress_pct` while running |
| `POST` | `/api/v1/dispatch-runs` | Register dual-pipeline run |
| `GET` | `/api/v1/dispatch-runs/active` | Active runs |
| `GET` | `/api/v1/dispatch-runs/active/for-chat/{chat_id}` | Per-chat active run |
| `PATCH` | `/api/v1/dispatch-runs/{id}` | Progress notification state |
| `POST` | `/api/v1/lookup` | Sync single-SKU |
| `GET` | `/api/v1/health` | Liveness |

Auth: `X-API-Key`. Default job sites: `gm`, `ml`, `vw`, `eu`, `pecadireta`.

### StokAPI (`muvstok-api/`)

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/api/v1/muvstok/jobs` | 202 Accepted |
| `GET` | `/api/v1/muvstok/jobs/{id}` | Status + live `progress_pct` |
| `GET` | `/api/v1/muvstok/health` | Liveness |

Auth: `X-API-Key`. Paths/tables keep `muvstok` prefix internally.

## Quality gates

```bash
make -C scrapers test lint
make check-muvstok
python3 scripts/sync_workflow_code_from_shared.py   # after n8n/src edits
```

## Deprecated

- `cdp_muvstok-api_starter` (`PXLHDzRbBVgs8Xl2`)
- `muvstok_job_sender` / `muvstok_job_receiver`
- Legacy `cdp_analise` / `cdp_resultado`
