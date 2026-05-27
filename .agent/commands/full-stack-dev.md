# full-stack-dev

**Purpose:** Run Postgres, Redis, and both services locally for dual-pipeline integration.

## Quick start (deps only + host APIs)

```bash
make setup          # copy .env examples, start postgres + redis
make migrate-scraper
make dev-scraper    # :8000 in scrapers/
# second terminal:
make dev-stokapi    # :8001
```

## Docker full stack (all containers)

```bash
cp scrapers/.env.example scrapers/.env
cp muvstok-api/.env.example muvstok-api/.env
# Edit API keys and DB URLs for docker hostnames (postgres, redis)

make dev-full       # docker compose --profile full up -d --build
```

Compose profiles:

| Profile | Services |
|---------|----------|
| *(default)* | `postgres`, `redis` |
| `scraper` | + `scraper-api`, `scraper-worker` |
| `stokapi` | + `stokapi-api`, `stokapi-worker` |
| `full` | all of the above |

Ports: scraper **8000**, StokAPI **8001**, Postgres **5432**, Redis **6379**.

## Per-service only

```bash
make -C scrapers dev                    # scraper :8000
cd muvstok-api && make dev              # stokapi docker (port 8000 in service compose)
```

## n8n / smoke

- Router code inject (no publish): `make sync-n8n-prep`
- Production smoke (needs API keys): `make smoke-cache`

**Platform env:** copy [`.env.example`](../../.env.example) → `.env` for `CDP_SCRAPER_API_BASE`, `CDP_STOKAPI_API_BASE`, n8n URLs.
