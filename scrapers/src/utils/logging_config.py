"""Structured logging configuration using structlog."""

import logging
import sys

import structlog

from src.config import settings

_CONFIGURED = False


def setup_logging() -> None:
    """Configure structlog for the application.

    Uses stdlib logging so Celery workers emit correct log levels instead of
    treating structlog PrintLogger stdout as WARNING on ForkPoolWorker.

    - JSON output in production (LOG_FORMAT=json)
    - Pretty console output in development (LOG_FORMAT=console)
    - Filters sensitive fields from log output
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = _log_level_to_int(settings.log_level)

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _filter_sensitive_fields,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    _CONFIGURED = True


def _filter_sensitive_fields(
    logger: object, method_name: str, event_dict: dict
) -> dict:
    """Remove sensitive data from log output."""
    sensitive_keys = {"password", "token", "secret", "api_key", "credential"}
    for key in list(event_dict.keys()):
        if any(s in key.lower() for s in sensitive_keys):
            event_dict[key] = "***REDACTED***"
    return event_dict


def _log_level_to_int(level: str) -> int:
    """Convert string log level to integer."""
    return getattr(logging, level.upper(), logging.INFO)
