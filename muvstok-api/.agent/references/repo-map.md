# Repo Map

## Production Package

- `app/main.py`: FastAPI app factory, route registration, exception handlers.
- `app/api/`: dependencies and route handlers.
- `app/schemas/`: Pydantic request, response, and callback contracts.
- `app/services/`: business orchestration.
- `app/repositories/`: SQLAlchemy persistence boundaries.
- `app/clients/`: Redis, Muvstok, Key Vault, and callback clients.
- `app/db/`: SQLAlchemy models, session setup, and Alembic migrations.
- `app/domain/`: status enums, events, and small domain models.
- `app/workers/`: Redis worker loop and job/SKU processors.
- `app/observability/`: metrics, tracing, and context helpers.
- `app/core/`: config, logging, security helpers, and exceptions.

## Docs And Specs

- `README.md`: service overview and CDP dual-pipeline context.
- `specs/`: 12 planning specs defining contracts and constraints.
- `docs/PRODUCTION_AUDIT.md`: live audit results and gap analysis.
- `docs/CDP_DUAL_PIPELINE_ARCHITECTURE.md`: pointer to monorepo dual pipeline doc.
- `.agent/`: durable AI-agent workspace (rules, memory, skills, standards, commands).

## n8n

- `n8n/workflows/cdp_stokapi.json`: **production** callback receiver (`muvstok-result`).
- `n8n/sdk/`: TypeScript SDK sources for MCP deployment.
- `n8n/settings/cdp_stokapi.json`: workflow metadata and env requirements.
- `n8n/lib/`: shared helper functions (sheet formatting).
- `n8n/docs/MUVSTOK_N8N_WORKFLOW_GUIDE.md`: receiver operations, sheets, callbacks.

**Production dispatch** is in monorepo `cdp_router` (`n8n/workflows/`), Code source `n8n/src/router_stokapi.js`. Deprecated: `cdp_muvstok-api_starter`, removed `muvstok_job_*.json`.

## Runtime And Tooling

- `main.py`: Uvicorn entrypoint for `app.main:app`.
- `pyproject.toml`: Python 3.12 project metadata, dependencies, ruff, mypy, pytest config.
- `Makefile`: `check-specs` and `azure-test` wrappers.
- `docker/`: Dockerfiles (API + worker) and local compose stack.
- `scripts/deploy_muv_api.sh`, `scripts/deploy_muv_worker.sh`: Azure deploy.
- `tests/`: test directories exist, but tests are not implemented yet.
