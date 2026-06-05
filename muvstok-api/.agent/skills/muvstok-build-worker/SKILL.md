---
name: muvstok-build-worker
description: Implement Muvstok worker and SKU processing behavior. Use when changing app/workers, job processing, SKU-by-SKU Muvstok calls, raw snapshot persistence, governance checks, callback orchestration, retry handling, or worker resumability.
---

# Muvstok Worker

## Overview

Use this skill to build the worker pipeline without losing resumability, durable state, or queue safety.

## Read First

- `.agent/rules.md`
- `.agent/memory/implementation-state.md`
- `specs/003-job-lifecycle.md`
- `specs/010-queue-processing.md`
- `app/workers/redis_worker.py`
- `app/workers/job_processor.py`
- `app/workers/sku_processor.py`
- `app/services/`
- `app/repositories/`
- `app/clients/muvstok_client.py`

## Workflow

1. Load job and pending or retryable SKU items from PostgreSQL.
2. Mark job and SKU states durably before external work.
3. Process one SKU at a time within a job.
4. Fetch or refresh token through the auth and Key Vault boundary.
5. Call Muvstok through `MuvstokClient`.
6. Persist raw snapshots before finalizing SKU success.
7. Classify result semantics separately from processing status:
   `FOUND_PRICE`, `NO_PRICE`, `NOT_FOUND`, `BLOCKED`, `TIMEOUT`, `ERROR`, or
   `NOT_QUERIED`; set `has_valid_price=true` only for positive usable sale price.
8. Record normalized errors for failures.
9. Derive final job status from SKU counts and callback outcome.
10. Ack Redis only after durable terminal or resumable state.
11. Update implementation state and known issues as placeholders become real.

## Validation

- Unit-test status transitions and retry classification.
- Integration-test Redis, PostgreSQL, and worker restart behavior in Azure.
- E2E-test job submission through callback completion in Azure.
- Run `uv run ruff check .` and `uv run mypy .`.

## Watch Points

- Worker restart must be able to resume from PostgreSQL state.
- Callback failure does not invalidate raw stored data.
- `status=succeeded` is worker lifecycle only; callback/reporting success requires
  `sku_result=FOUND_PRICE` and `has_valid_price=true`.
- Receiver/sheet seller fields are `uf`, `empresa`, `cnpj` after `vendedor`;
  normalize any upstream `estado` aliases to `uf`.
- Do not expand to parallel SKU processing without explicit business approval.
