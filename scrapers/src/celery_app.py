"""Celery application for durable scraper job execution."""

from celery import Celery
from celery.signals import worker_process_init

from src.config import settings
from src.utils.logging_config import setup_logging


@worker_process_init.connect  # type: ignore[misc]
def _configure_worker_logging(**_kwargs: object) -> None:
    """Configure structlog once per forked worker child process."""
    setup_logging()

celery_app = Celery(
    "cdp_scraper",
    broker=settings.resolved_celery_broker_url,
    backend=settings.resolved_celery_result_backend,
    include=["src.tasks.scrape_jobs"],
)

celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    enable_utc=True,
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    task_time_limit=settings.celery_task_time_limit_seconds,
    task_track_started=True,
    timezone="UTC",
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
)
