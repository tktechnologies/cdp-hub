# Coding Standards (Platform)

## Architecture

- Business logic in services, not route handlers.
- Dependency direction: route/worker → service → repository/client → external systems.
- Prefer small, production-shaped changes over unused scaffolding.
- No shared Python packages between `scrapers/` and `muvstok-api/`.

## Python

- Python 3.12+, typed interfaces, ruff line length 100.
- Pydantic v2 at API boundaries; async I/O consistent with each service.
- mypy strict in muvstok-api; match scraper typing conventions when editing scrapers.
- Comments only for non-obvious business logic.

## Data and security

- No secrets in code, logs, commits, or agent memory files.
- Preserve `correlation_id` / `job_id` / `batch_group_id` through logs and callbacks.

## Service-specific

- StokAPI: [muvstok-api/.agent/standards/coding-standards.md](../../muvstok-api/.agent/standards/coding-standards.md)
- Scraper: [scrapers/.agent/rules.md](../../scrapers/.agent/rules.md)
