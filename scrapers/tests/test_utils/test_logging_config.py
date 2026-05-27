"""Tests for structured logging setup."""

import json
import logging

import structlog

from src.utils import logging_config


def _reset_logging() -> None:
    logging_config._CONFIGURED = False
    logging.getLogger().handlers.clear()


def test_setup_logging_uses_stdlib_factory(monkeypatch) -> None:
    _reset_logging()
    monkeypatch.setattr(logging_config.settings, "log_format", "json")
    monkeypatch.setattr(logging_config.settings, "log_level", "INFO")

    logging_config.setup_logging()

    config = structlog.get_config()
    assert isinstance(config["logger_factory"], structlog.stdlib.LoggerFactory)


def test_info_logs_emit_at_info_level(monkeypatch) -> None:
    _reset_logging()
    monkeypatch.setattr(logging_config.settings, "log_format", "json")
    monkeypatch.setattr(logging_config.settings, "log_level", "INFO")

    records: list[logging.LogRecord] = []

    class CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    logging_config.setup_logging()
    capture = CaptureHandler()
    logging.getLogger().addHandler(capture)

    logger = structlog.get_logger("test")
    logger.info("sku search completed", site="vw", sku="3B0867334")

    assert len(records) == 1
    assert records[0].levelno == logging.INFO
    msg = records[0].msg
    payload = msg if isinstance(msg, dict) else json.loads(msg)
    assert payload["event"] == "sku search completed"
    assert payload["level"] == "info"
    assert payload["site"] == "vw"
