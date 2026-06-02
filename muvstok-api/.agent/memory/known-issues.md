# Known Issues

**Last reviewed:** 2026-06-01

## Documentation

- Use monorepo `make sync-n8n` and `scripts/n8n_publish.py` (REST + MCP publish). Legacy `sync_n8n_workflows.py` / standalone sender docs are obsolete.
- Production dispatch is **cdp_router** inline HTTP only — not Execute Workflow or `muvstok_job_*.json`.

## Open risks

- Muvstok API contracts are reverse-engineered; rate limits and max batch size need confirmation before large runs.
- Redis needs persistence/monitoring plan for heavy production load.
- Callback SSRF blocks obvious localhost; full private-range blocking deferred.
- `GovernanceService` is a stub.
- Job create commits PG before Redis publish — publish failure leaves pending jobs.
- Historical dead-letter queue may need requeue or purge.

## Tests

- Contract tests: `tests/test_contracts/`
- Full suite: `uv run pytest tests/ -v`

## Deferred

- One queue message per SKU (parallel processing).
- Synchronous live lookup unless required.
- Production API-key rotation workflow.
- Full SSRF protection for callback URLs.
