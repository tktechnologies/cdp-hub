"""Proxy rotation helpers for Playwright scraper contexts."""

from dataclasses import dataclass
from itertools import cycle
from threading import Lock
from urllib.parse import urlparse

import structlog

from src.config import settings

logger = structlog.get_logger()


@dataclass(frozen=True)
class ProxyEndpoint:
    """A single outbound proxy endpoint."""

    server: str
    username: str | None = None
    password: str | None = None

    @classmethod
    def from_url(cls, url: str) -> "ProxyEndpoint":
        """Parse a proxy URL into Playwright's proxy format."""
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.hostname:
            raise ValueError("Proxy URL must include scheme and host")

        host = parsed.hostname
        port = f":{parsed.port}" if parsed.port else ""
        server = f"{parsed.scheme}://{host}{port}"
        return cls(server=server, username=parsed.username, password=parsed.password)

    def to_playwright(self) -> dict[str, str]:
        """Return a Playwright-compatible proxy dict."""
        proxy = {"server": self.server, "bypass": settings.proxy_bypass}
        if self.username:
            proxy["username"] = self.username
        if self.password:
            proxy["password"] = self.password
        return proxy


class ProxyManager:
    """Round-robin proxy selector shared by scraper instances."""

    def __init__(self, proxy_urls: list[str]) -> None:
        self._lock = Lock()
        self._proxies = [ProxyEndpoint.from_url(url) for url in proxy_urls if url.strip()]
        self._cycle = cycle(self._proxies) if self._proxies else None

    @property
    def enabled(self) -> bool:
        """Return whether proxy rotation can be used."""
        return settings.proxy_rotation_enabled and bool(self._proxies)

    def next_proxy(self) -> ProxyEndpoint | None:
        """Return the next proxy endpoint in round-robin order."""
        if not self.enabled or self._cycle is None:
            return None
        with self._lock:
            return next(self._cycle)


_proxy_manager: ProxyManager | None = None


def get_proxy_manager() -> ProxyManager:
    """Return the process-wide proxy manager."""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager(settings.proxy_urls)
        if settings.proxy_rotation_enabled and not _proxy_manager.enabled:
            logger.warning("Proxy rotation enabled but no proxy URLs are configured")
    return _proxy_manager


def reset_proxy_manager() -> None:
    """Reset singleton state for tests or settings reloads."""
    global _proxy_manager
    _proxy_manager = None
