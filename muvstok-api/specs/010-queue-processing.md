# Queue Processing

## Queue Choice

Use Redis Streams with consumer groups.

## Stream

- job stream: `muvstok:jobs`
- consumer group: `muvstok-workers`
- dead-letter stream: `muvstok:jobs:dead-letter`

## Message Shape

```json
{
  "job_id": "uuid",
  "correlation_id": "uuid",
  "sku_count": 1000
}
```

## Rules

- Do not put the full SKU list in Redis.
- PostgreSQL owns all SKU item state.
- Workers acknowledge messages only after the job reaches a durable terminal or resumable state.
- Pending Redis messages must be inspectable and recoverable.
- Poison jobs move to the dead-letter stream with error metadata.

## Scaling

Scale workers horizontally across jobs. Keep Muvstok requests SKU-by-SKU inside each job until the business allows more parallelism.
