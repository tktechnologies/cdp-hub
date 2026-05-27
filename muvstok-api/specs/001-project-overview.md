# Project Overview

## Purpose

Build a scalable Muvstok ingestion API that accepts SKU jobs, processes them SKU by SKU in background workers, stores raw and operational data in PostgreSQL, and delivers results through callbacks.

The Muvstok API is deployed as its own FastAPI container, separate from the existing scraper API container. Both services can use the same PostgreSQL server/database for later result matching, but they must keep clear table ownership boundaries.

## Version 1 Scope

- FastAPI job submission and job inspection API.
- A separately deployed Muvstok FastAPI container.
- PostgreSQL-backed job, SKU item, snapshot, callback, audit, error, token metadata, and queue tracking.
- Dedicated Muvstok API result storage in `muvstok_api_data`, separate from scraper-owned tables.
- Redis Streams queueing with consumer groups.
- Worker processing that can handle jobs with thousands of SKUs without loading unbounded data into memory.
- Muvstok token access through Azure Key Vault.
- Azure-hosted testing and validation.

## Deferred Scope

- One queue message per SKU.
- Advanced analytics dashboards.
- Redis caching beyond queue needs.
- Synchronous live lookup unless explicitly required.

## Key Decisions

- Redis Streams replaces Azure Service Bus to reduce Azure service footprint and cost.
- PostgreSQL is the durable source of truth; Redis is coordination, not permanent business storage.
- The scraper API and Muvstok API remain separate application containers and separate write owners, even when they share a database.
- Workers scale horizontally across jobs while preserving SKU-by-SKU Muvstok calls inside a job.
- Tests are designed to run in Azure cloud environments, not locally.

## Risks

- Self-hosted Redis is cheaper but needs persistence, backup, monitoring, and restart planning.
- Large jobs need careful batching and frequent progress persistence.
- Callback SSRF, token leakage, and idempotency bugs are high-risk areas.

## Open Questions

- Exact Muvstok auth and SKU endpoint contracts.
- Maximum expected SKU count per job.
- Expected throughput, rate limits, and callback SLA.
- Whether Redis will be self-hosted or managed.
