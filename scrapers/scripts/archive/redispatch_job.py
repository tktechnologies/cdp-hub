#!/usr/bin/env python3
"""Re-queue an existing scrape job to Celery (same job_id)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_id", help="Existing scrape job UUID")
    parser.add_argument(
        "--payload",
        required=True,
        help="Path to JSON file with ScrapeJobRequest fields (items, sites, callback_url, priority)",
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    from src.tasks.scrape_jobs import execute_scrape_job

    result = execute_scrape_job.delay(args.job_id, payload)
    print(json.dumps({"job_id": args.job_id, "celery_task_id": result.id}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
