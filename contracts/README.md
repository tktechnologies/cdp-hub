# CDP Shared Contracts

JSON Schema definitions for cross-service and n8n integration.

**Keep in sync with:**

- Scraper: `scrapers/src/models/schemas.py`
- StokAPI: `muvstok-api/app/schemas/requests.py`, `app/schemas/callbacks.py`

| Schema | Purpose |
|--------|---------|
| [scraper-job.schema.json](scraper-job.schema.json) | `POST /api/v1/jobs` |
| [stokapi-job.schema.json](stokapi-job.schema.json) | `POST /api/v1/muvstok/jobs` |
| [scraper-callback.schema.json](scraper-callback.schema.json) | `scraper-result` webhook (`ScrapeJobResult`) |
| [stokapi-callback.schema.json](stokapi-callback.schema.json) | `muvstok-result` webhook (`MuvstokCallbackPayload`) |
| [dispatch-run.schema.json](dispatch-run.schema.json) | Scraper `POST/PATCH /api/v1/dispatch-runs` (dual-pipeline progress) |

## Change process

1. Update Pydantic models in the owning service.
2. Update the matching schema here.
3. Update n8n receiver workflow if callback shape changes.
4. Run contract tests: `scrapers/tests/test_contracts/`, `muvstok-api/tests/test_contracts/` (CI: `.github/workflows/ci-contracts.yml`).
5. Document in PR.

## Result semantics

Callback schemas use canonical reporting fields:

- `sku_result` / `status_resultado`:
  `FOUND_PRICE`, `NO_PRICE`, `NOT_FOUND`, `BLOCKED`, `TIMEOUT`, `ERROR`,
  `NOT_QUERIED`.
- `source_health`: `WORKING`, `BLOCKED`, `TIMEOUT`, `ERROR`, `NOT_QUERIED`.
  `WORKING` is canonical; legacy API Diversos `OK` is accepted only for
  backward compatibility and maps to `WORKING` for reports.
- `has_valid_price`: true only when a usable positive price exists.
- Scraper result seller metadata uses `seller_uf`, `seller_company_name`, and
  `seller_cnpj`; Sheets flatten this as `uf`, `empresa`, and `cnpj` after
  `vendedor`. `estado` is not a canonical output field.

Never infer found-price success from row existence, `status=succeeded`, or
`exact_match` alone. `BLOCKED` is a separate outcome from `NOT_FOUND`.

Platform API notes: [.agent/standards/api-design.md](../.agent/standards/api-design.md).
