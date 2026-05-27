import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings

EXTRA_LOG_FIELDS = (
    "service",
    "environment",
    "correlation_id",
    "job_id",
    "sku",
    "event_name",
    "status",
    "duration_ms",
    "attempt",
    "queue_message_id",
    "worker_id",
    "error_code",
    "error_type",
    "azure_resource",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in EXTRA_LOG_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(settings: Settings) -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    logging.getLogger("muvstok").info(
        "logging_configured",
        extra={
            "event_name": "logging_configured",
            "environment": settings.environment,
            "service": "muvstok-api",
        },
    )
