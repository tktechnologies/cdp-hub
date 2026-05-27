# run-quality-gates

**Purpose:** Run the platform quality gates before merge or deploy. Local results are a fast signal; Azure-hosted validation remains authoritative for StokAPI production work (see `muvstok-api/tests/README.md`).

## Prerequisites

- `uv` installed for StokAPI (`muvstok-api/`)
- Python 3.12+ and project deps for Scraper (`scrapers/`)
- Optional: Docker for `make dev` (Postgres + Redis) when running integration tests

## Platform (monorepo root)

```bash
# Lint both services
make lint

# Scraper unit + contract tests
make test

# StokAPI lint + typecheck + unit/contract tests
make check-muvstok
cd muvstok-api && uv run pytest tests/ -v --tb=short
```

## Scraper only

```bash
make -C scrapers test lint
```

Includes parser smoke tests (`tests/test_scrapers/`) and JSON Schema contract tests (`tests/test_contracts/`).

## StokAPI only

```bash
cd muvstok-api
uv run ruff check .
uv run mypy .
uv run pytest tests/ -v --tb=short
bash scripts/check_specs.sh
```

## Shared contracts

JSON Schemas live in [`contracts/`](../../contracts/). Contract tests validate:

| Schema | Validated by |
|--------|----------------|
| `stokapi-job.schema.json` | `muvstok-api/tests/test_contracts/` |
| `stokapi-callback.schema.json` | `muvstok-api/tests/test_contracts/` |
| `scraper-job.schema.json` | `scrapers/tests/test_contracts/` |
| `scraper-callback.schema.json` | `scrapers/tests/test_contracts/` |

When changing Pydantic models in either service, update the matching schema and re-run both contract test suites.

## n8n (manual approval)

Router Code edits: `n8n/src/` → `python3 scripts/sync_workflow_code_from_shared.py` → `make sync-n8n` (user approval only). See [.agent/skills/n8n-router-sync/SKILL.md](../skills/n8n-router-sync/SKILL.md).

## Azure Monitor alerting

`muvstok-api/infra/` is not yet provisioned (no Bicep modules in-repo). Until infrastructure lands:

- **Planned alerts** (documented in `scrapers/docs/PRODUCTION_PLAN.md` and `scrapers/docs/AZURE_REBUILD_PLAN.md`): failed jobs, elevated `blocked` scraper rate, worker crashes, Redis/queue depth.
- **Current signals:** Prometheus metrics endpoints (Scraper + StokAPI), structured logs (`event_name` fields), n8n execution history for `cdp_router` / `cdp_scraper` / `cdp_stokapi`.
- **After Bicep:** wire Azure Monitor action groups (email/Teams) to Application Insights alert rules for HTTP 5xx, queue lag, and callback delivery failures.

## CI recommendations

| Job | Command | Notes |
|-----|---------|-------|
| `scraper-test` | `make -C scrapers test` | Fast; no browser required when `MOCK_SCRAPERS=true` |
| `scraper-lint` | `make -C scrapers lint` | ruff + mypy |
| `stokapi-lint` | `cd muvstok-api && uv run ruff check . && uv run mypy .` | |
| `stokapi-test` | `cd muvstok-api && uv run pytest tests/ -v` | No Postgres required for current unit/contract tests |
| `contracts` | Run both test suites above | Fails if schemas drift from models |
| `stokapi-specs` | `cd muvstok-api && bash scripts/check_specs.sh` | Spec consistency |

Optional: add a root `make test-all` target that runs Scraper + StokAPI pytest in one step.

## Pass criteria

- All commands exit 0
- No new ruff/mypy violations in touched paths
- Contract tests green after schema or model changes
- n8n sync only when explicitly requested
