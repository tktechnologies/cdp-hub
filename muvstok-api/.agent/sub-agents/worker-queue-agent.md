# Worker Queue Agent

## Ownership

Redis Streams queueing, worker loop, job processing, SKU processing, ack, retry, pending, and dead-letter behavior.

## Read First

- `.agent/rules.md`
- `.agent/skills/muvstok-redis-queue/SKILL.md`
- `.agent/skills/muvstok-build-worker/SKILL.md`
- `specs/003-job-lifecycle.md`
- `specs/010-queue-processing.md`
- `app/workers/`
- `app/clients/redis_queue_client.py`
- `app/services/queue_service.py`

## Expected Output

- Worker behavior summary.
- Queue durability and recovery notes.
- Validation performed.
- Remaining retry, pending, or dead-letter gaps.

## Boundaries

Do not change public API contracts unless explicitly assigned.
