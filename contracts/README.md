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
4. Run service quality gates and document in PR.

Platform API notes: [.agent/standards/api-design.md](../.agent/standards/api-design.md).
