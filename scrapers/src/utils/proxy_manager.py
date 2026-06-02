"""Proxy rotation helpers for Playwright scraper contexts."""

from dataclasses import dataclass
from hashlib import sha256
from itertools import cycle
from threading import Lock
from urllib.parse import quote, urlparse

import structlog

from src.config import settings

logger = structlog.get_logger()


@dataclass(frozen=True)
class ProxyEndpoint:
    """A single outbound proxy endpoint."""

    server: str
    username: str | None = None
    password: str | None = None

    @property
    def identity(self) -> str:
        """Stable non-secret identity for logs, metrics, and state partitioning."""
        principal = self.username or ""
        digest = sha256(f"{self.server}|{principal}".encode()).hexdigest()
        return digest[:12]

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

    def to_httpx_url(self) -> str:
        """Return a proxy URL with credentials for HTTP clients."""
        if not self.username and not self.password:
            return self.server
        parsed = urlparse(self.server)
        username = quote(self.username or "", safe="")
        password = quote(self.password or "", safe="")
        credentials = f"{username}:{password}@"
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        return f"{parsed.scheme}://{credentials}{host}{port}"


class ProxyManager:
    """Round-robin proxy selector shared by scraper instances."""

    def __init__(self, proxy_urls: list[str]) -> None:
        self._lock = Lock()
        self._proxies = [ProxyEndpoint.from_url(url) for url in proxy_urls if url.strip()]
        self._cycle = cycle(self._proxies) if self._proxies else None
        self._affinity: dict[str, ProxyEndpoint] = {}

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

    def proxy_for_site(self, site_id: str) -> ProxyEndpoint | None:
        """Return a stable proxy for one site when affinity is enabled."""
        if not self.enabled:
            return None
        if not settings.proxy_affinity_enabled:
            return self.next_proxy()
        with self._lock:
            if site_id not in self._affinity:
                assert self._cycle is not None
                self._affinity[site_id] = next(self._cycle)
            return self._affinity[site_id]


_proxy_manager: ProxyManager | None = None


def get_proxy_manager() -> ProxyManager:
    """Return the process-wide proxy manager."""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager(settings.proxy_urls)
        if settings.proxy_rotation_enabled and not _proxy_manager.enabled:
            if settings.proxy_fail_closed:
                raise RuntimeError("Proxy rotation enabled but no proxy URLs are configured")
            logger.warning("Proxy rotation enabled but no proxy URLs are configured")
    return _proxy_manager


def reset_proxy_manager() -> None:
    """Reset singleton state for tests or settings reloads."""
    global _proxy_manager
    _proxy_manager = None
