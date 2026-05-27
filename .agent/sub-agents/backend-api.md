# Backend API Agent (Platform)

## Ownership

Cross-service HTTP contracts, shared JSON Schema in `contracts/`, dispatch-run registry, and coordinated API changes that affect both Scraper and StokAPI.

## Read First

- [.agent/standards/api-design.md](../standards/api-design.md)
- [contracts/README.md](../../contracts/README.md)
- [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)
- `scrapers/src/models/schemas.py`
- `muvstok-api/app/schemas/`

## Expected Output

- Contract diff summary (request + callback).
- Files changed per owning service.
- Validation performed (`make -C scrapers test`, `make check-muvstok`).
- n8n receiver impact if callback shape changed.

## Boundaries

Do not edit Playwright scrapers, Redis Streams worker loops, or `n8n/src/` unless explicitly assigned. Delegate scraper-only work to `scrapers/.agent/`, StokAPI-only to `muvstok-api/.agent/`.
