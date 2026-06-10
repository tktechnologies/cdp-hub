# Archived StokAPI ops scripts

Ad-hoc utilities kept for reference. Not wired in Makefile or CI.

| Script | Purpose |
|--------|---------|
| `import_company_locations.py` | Import dealership metadata to PostgreSQL |
| `check_db_muvstok.py` | Quick database health check |
| `drain_muvstok_queue.py` | Redis stream drain and stats |

Run from `muvstok-api/` with `uv run python scripts/archive/<script>.py`.
