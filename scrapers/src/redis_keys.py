"""Redis key naming conventions for the scraper service.

Platform-wide layout: docs/DATABASE.md
"""

# Celery broker + result backend (settings.redis_url) — Redis logical DB 0.

# Per-site SKU scrape snapshots (settings.scrape_cache_redis_url) — Redis logical DB 1.
SCRAPE_CACHE_PREFIX = "scrape:v1:"
# Full key: scrape:v1:{site}:{brand_key}:{sku_key}

# Reserved — hot dispatch-run snapshots (PostgreSQL dispatch_runs is authoritative today).
DISPATCH_RUN_PREFIX = "dispatch:run:"
# Full key: dispatch:run:{run_id}

# Reserved — ephemeral progress poll state for n8n / Telegram (not yet written in production).
PROGRESS_PREFIX = "progress:"
# Full key: progress:{chat_id} or progress:{run_id}
