"""Celery tasks for scrape job execution."""

import asyncio
from typing import Any

import structlog

from src.celery_app import celery_app
from src.models.schemas import ScrapeJobRequest
from src.scrapers import shutdown_all_scrapers
from src.services.orchestrator import Orchestrator
from src.utils.logging_config import setup_logging

logger = structlog.get_logger()


@celery_app.task(name="src.tasks.scrape_jobs.execute_scrape_job")
def execute_scrape_job(job_id: str, request_payload: dict[str, Any]) -> dict[str, str]:
    """Run a queued scrape job in a Celery worker process."""
    setup_logging()
    request = ScrapeJobRequest.model_validate(request_payload)

    async def _run() -> None:
        try:
            await Orchestrator().execute_queued_job(job_id, request)
        finally:
            await shutdown_all_scrapers()

    logger.info("Celery scrape job started", job_id=job_id)
    asyncio.run(_run())
    logger.info("Celery scrape job finished", job_id=job_id)
    return {"job_id": job_id, "status": "finished"}
