# Known Issues

Last reviewed: 2026-05-26.

## Documentation drift

- `scripts/sync_n8n_workflows.py` and `n8n/sdk/muvstok_*.workflow.ts` may reference removed `muvstok_job_sender.json` / `muvstok_job_receiver.json`. Use monorepo `make sync-n8n` and `cdp_stokapi.json` only.
- README and older guides described a standalone n8n sender; production uses **cdp_router** inline dispatch.

## Open Risks

- Exact Muvstok auth and SKU endpoint contracts are based on reverse-engineering, not official docs.
- Maximum expected SKU count, throughput, rate limits, and callback SLA need confirmation before scaling past ~50 SKU batches.
- Redis is self-hosted; needs persistence, backup, monitoring, and restart planning before heavy production load.
- Callback SSRF protection blocks obvious localhost but not full private-network ranges.
- `GovernanceService` is a stub — no automated consistency rules yet.
- `scripts/azure_test.sh` is not wired to Azure CI/CD yet.
- There are no real test files beyond `tests/README.md`.
- Job creation commits PostgreSQL before publishing to Redis; queue publish failure leaves a pending job needing recovery.
- ~130 historical dead-lettered jobs from worker bring-up may need requeue or purge.

## Deferred Scope

- One queue message per SKU (parallel SKU processing).
- Advanced analytics dashboards.
- ~~Redis caching beyond queue needs.~~ Done 2026-05-29: per-SKU result cache (`app/services/sku_cache.py`, 24h) + in-job memo; duplicates no longer re-request upstream and jobs return N results.
- Synchronous live lookup (`/api/v1/muvstok`) unless explicitly required.
- Final callback HMAC contract.
- Production API-key storage, rotation, and revocation workflow.
- Full SSRF protection for callback URLs (private IP range blocking).
