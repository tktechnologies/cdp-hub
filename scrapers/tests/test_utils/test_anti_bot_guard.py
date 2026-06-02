"""Tests for anti-bot circuit breaker behavior."""

from src.config import settings
from src.utils.anti_bot_guard import AntiBotCircuitBreaker


def test_circuit_breaker_opens_after_threshold(monkeypatch):
    monkeypatch.setattr(settings, "anti_bot_circuit_breaker_enabled", True)
    monkeypatch.setattr(settings, "anti_bot_circuit_breaker_threshold", 2)
    monkeypatch.setattr(settings, "anti_bot_circuit_breaker_cooldown_seconds", 60)
    breaker = AntiBotCircuitBreaker()

    breaker.record_block("ml", "proxy-a", "HTTP 403")
    assert breaker.is_open("ml", "proxy-a")[0] is False

    breaker.record_block("ml", "proxy-a", "HTTP 403")
    is_open, retry_after, reason = breaker.is_open("ml", "proxy-a")

    assert is_open is True
    assert retry_after > 0
    assert reason == "HTTP 403"


def test_circuit_breaker_success_resets(monkeypatch):
    monkeypatch.setattr(settings, "anti_bot_circuit_breaker_enabled", True)
    monkeypatch.setattr(settings, "anti_bot_circuit_breaker_threshold", 1)
    monkeypatch.setattr(settings, "anti_bot_circuit_breaker_cooldown_seconds", 60)
    breaker = AntiBotCircuitBreaker()

    breaker.record_block("ml", "proxy-a", "HTTP 403")
    assert breaker.is_open("ml", "proxy-a")[0] is True

    breaker.record_success("ml", "proxy-a")
    assert breaker.is_open("ml", "proxy-a")[0] is False
