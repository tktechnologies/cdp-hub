# Archived scraper ops scripts

Ad-hoc or meeting-era utilities kept for reference. Not wired in Makefile or CI.

| Script | Purpose |
|--------|---------|
| `batch_meeting_skus.py` | Batch meeting SKUs locally |
| `summarize_meeting_batch.py` | Markdown summary from batch JSON |
| `redispatch_job.py` | Re-queue a Celery job by ID |
| `replay_scraper_telegram_notify.py` | Replay webhook for Telegram notification fix |

Run from `scrapers/` with `uv run python scripts/archive/<script>.py`.
