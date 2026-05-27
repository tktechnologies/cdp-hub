---
name: muvstok-redis-queue
description: Work with Muvstok Redis Streams queue behavior. Use when changing Redis publish, consume, consumer group, ack, retry, pending recovery, dead-letter, queue persistence, queue message recording, or app/clients/redis_queue_client.py and app/services/queue_service.py.
---

# Muvstok Redis Queue

## Overview

Use this skill to keep Redis as lightweight coordination while PostgreSQL remains the durable source of truth.

## Read First

- `.agent/rules.md`
- `.agent/memory/implementation-state.md`
- `specs/010-queue-processing.md`
- `app/clients/redis_queue_client.py`
- `app/services/queue_service.py`
- `app/repositories/queue_repository.py`
- `app/workers/redis_worker.py`

## Workflow

1. Keep Redis job payloads small: `job_id`, `correlation_id`, and `sku_count`.
2. Ensure consumer groups are created idempotently.
3. Record published queue messages in PostgreSQL.
4. Ack messages only after durable terminal or resumable state.
5. Move poison jobs to the dead-letter stream with error metadata.
6. Make pending messages inspectable and recoverable.
7. Add logs with `queue_message_id`, `job_id`, and `correlation_id`.
8. Update command recipes when Redis inspection commands become stable.

## Constants

- Job stream: `muvstok:jobs`
- Consumer group: `muvstok-workers`
- Dead-letter stream: `muvstok:jobs:dead-letter`

## Validation

- Test publish, consume, ack, pending, retry, and dead-letter flows in Azure-hosted Redis.
- Run `uv run ruff check .` and `uv run mypy .` after Python edits.
