# Job Lifecycle

## Parent Job States

- `pending`: stored in PostgreSQL but not yet published to Redis.
- `queued`: published to Redis Stream.
- `processing`: worker has started processing.
- `succeeded`: every SKU succeeded and callback succeeded or callback is not required.
- `partially_succeeded`: at least one SKU succeeded and at least one failed.
- `failed`: no SKU succeeded or the job cannot continue.
- `canceled`: reserved for future operator cancellation.

## SKU Item States

- `pending`
- `processing`
- `succeeded`
- `failed`
- `retrying`
- `skipped`

## Rules

- Workers process SKUs sequentially inside a job.
- Progress is persisted after each SKU or small batch.
- A worker restart must be able to resume from durable PostgreSQL state.
- Callback failure does not delete or invalidate stored raw data.

## Finalization

Final job status is derived from SKU counts and callback outcome. Partial success is valid and must produce a callback payload with item-level statuses.
