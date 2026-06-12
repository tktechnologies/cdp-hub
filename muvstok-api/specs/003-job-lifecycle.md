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

`succeeded` is a processing lifecycle state. It does not mean the SKU had a
price. Price/result semantics live in the canonical result fields:

- `sku_result`: `FOUND_PRICE`, `NO_PRICE`, `NOT_FOUND`, `BLOCKED`, `TIMEOUT`,
  `ERROR`, `NOT_QUERIED`.
- `source_health`: `OK`/`WORKING`, `BLOCKED`, `TIMEOUT`, `ERROR`,
  `NOT_QUERIED`.
- `has_valid_price`: true only for a positive usable sale price.

Examples:

- Upstream returns rows with sale price -> item `status=succeeded`,
  `sku_result=FOUND_PRICE`, `has_valid_price=true`.
- Upstream returns rows/evidence without sale price -> item `status=succeeded`,
  `sku_result=NO_PRICE`, `has_valid_price=false`.
- Upstream returns 404/no rows -> item `status=succeeded`,
  `sku_result=NOT_FOUND`, `has_valid_price=false`.
- Upstream blocks/denies access -> item `status=failed` or callback error item,
  `sku_result=BLOCKED`, `source_health=BLOCKED`.
- Sheet receivers write seller metadata as `vendedor`, `uf`, `empresa`, `cnpj`.
  Raw `estado` aliases are accepted only to normalize into `uf`.
- Rows are enriched from the dealership directory before persistence/callback so
  `uf` and related filial metadata are available to n8n. The directory loads
  from Postgres and may fall back to the configured directory CSV when enabled.
  The primary match is `codigoFilial`; when the upstream row omits that id, the
  fallback is an exact normalized branch/seller name that is unique in the
  directory.

## Rules

- Workers process SKUs sequentially inside a job.
- Progress is persisted after each SKU or small batch.
- A worker restart must be able to resume from durable PostgreSQL state.
- Callback failure does not delete or invalidate stored raw data.

## Finalization

Final job status is derived from SKU counts and callback outcome. Partial success is valid and must produce a callback payload with item-level statuses.
