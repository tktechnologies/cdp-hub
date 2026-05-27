# Project Memory

## Current Direction

API Diversos (StokAPI) is a FastAPI ingestion platform that accepts SKU jobs, stores durable state in PostgreSQL, queues lightweight job messages in Redis Streams, and processes Muvstok requests SKU by SKU in workers.

Production dispatch is via monorepo **cdp_router** (`n8n/src/router_stokapi.js`), not a standalone n8n sender. Callbacks are handled by **cdp_stokapi** in this repo.

## Version 1 Scope

- FastAPI job submission and job inspection API.
- PostgreSQL-backed job, SKU item, snapshot, callback, audit, error, token metadata, and queue tracking.
- Redis Streams queueing with consumer groups.
- Worker processing for jobs with thousands of SKUs without loading unbounded data into memory.
- Muvstok token access through Azure Key Vault.
- Azure-hosted testing and validation.

## Important Constraints

- Use Redis Streams instead of Azure Service Bus for version 1.
- Official tests run in Azure cloud environments, not locally.
- PostgreSQL is the durable source of truth; Redis is coordination, not permanent business storage.
- The system must handle jobs with thousands of SKUs.
- Workers may scale across jobs, but each job sends Muvstok requests SKU by SKU.
- Secrets belong in Azure Key Vault, never in logs or plain PostgreSQL fields.
- Production code lives under `app/`.
- The root `main.py` only starts `app.main:app` through Uvicorn.

## Open Questions

- Exact Muvstok auth and SKU endpoint contracts.
- Maximum expected SKU count per job.
- Expected throughput, rate limits, and callback SLA.
- Whether Redis will be self-hosted or managed.
