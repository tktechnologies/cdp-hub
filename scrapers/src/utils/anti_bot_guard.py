"""In-process anti-bot circuit breaker by site and network identity."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock

import structlog

from src.config import settings

logger = structlog.get_logger()


@dataclass
class CircuitState:
    consecutive_blocks: int = 0
    blocked_until: float = 0.0
    last_reason: str = ""


class AntiBotCircuitBreaker:
    """Cool down a site/proxy pair after repeated anti-bot blocks."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._states: dict[tuple[str, str], CircuitState] = {}

    def _key(self, site: str, proxy_identity: str | None) -> tuple[str, str]:
        return site, proxy_identity or "direct"

    def is_open(self, site: str, proxy_identity: str | None) -> tuple[bool, int, str]:
        """Return whether a site/proxy pair is cooling down."""
        if not settings.anti_bot_circuit_breaker_enabled:
            return False, 0, ""
        key = self._key(site, proxy_identity)
        now = time.monotonic()
        with self._lock:
            state = self._states.get(key)
            if not state or state.blocked_until <= now:
                return False, 0, ""
            return True, int(state.blocked_until - now), state.last_reason

    def record_block(self, site: str, proxy_identity: str | None, reason: str) -> None:
        """Record one block and open the circuit after the configured threshold."""
        if not settings.anti_bot_circuit_breaker_enabled:
            return
        key = self._key(site, proxy_identity)
        threshold = max(1, settings.anti_bot_circuit_breaker_threshold)
        cooldown = max(0, settings.anti_bot_circuit_breaker_cooldown_seconds)
        with self._lock:
            state = self._states.setdefault(key, CircuitState())
            state.consecutive_blocks += 1
            state.last_reason = reason
            if state.consecutive_blocks >= threshold and cooldown > 0:
                state.blocked_until = time.monotonic() + cooldown
                logger.warning(
                    "Anti-bot circuit breaker opened",
                    site=site,
                    proxy_identity=proxy_identity or "direct",
                    consecutive_blocks=state.consecutive_blocks,
                    cooldown_seconds=cooldown,
                    reason=reason,
                )

    def record_success(self, site: str, proxy_identity: str | None) -> None:
        """Reset consecutive block count after a non-blocked scrape."""
        key = self._key(site, proxy_identity)
        with self._lock:
            state = self._states.get(key)
            if state:
                state.consecutive_blocks = 0
                state.blocked_until = 0.0
                state.last_reason = ""

    def reset(self) -> None:
        """Reset all circuit state. Used by tests."""
        with self._lock:
            self._states.clear()


anti_bot_circuit_breaker = AntiBotCircuitBreaker()
