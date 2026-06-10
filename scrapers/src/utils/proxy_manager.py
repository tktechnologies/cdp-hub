"""Proxy rotation helpers for Playwright scraper contexts."""

from dataclasses import dataclass
from hashlib import sha256
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

    @property
    def host(self) -> str:
        """Proxy host/IP for logging and result metadata (no credentials)."""
        return urlparse(self.server).hostname or ""

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


def sku_scope_key(sku: str, brand: str = "") -> str:
    """Stable key for proxy binding across all sites in one SKU lookup."""
    normalized_sku = "".join(ch for ch in sku.strip().upper() if ch.isalnum())
    normalized_brand = "".join(ch for ch in brand.strip().lower() if ch.isalnum())
    return f"{normalized_sku}|{normalized_brand}"


class ProxyManager:
    """Proxy selector — strict alternation per SKU (all sites share one IP per SKU)."""

    def __init__(self, proxy_urls: list[str]) -> None:
        self._lock = Lock()
        self._proxies = [ProxyEndpoint.from_url(url) for url in proxy_urls if url.strip()]
        self._affinity: dict[str, ProxyEndpoint] = {}
        self._last_index: int | None = None
        self._last_identity: str | None = None
        self._last_host: str | None = None
        self._sku_key: str | None = None
        self._sku_proxy: ProxyEndpoint | None = None

    @property
    def enabled(self) -> bool:
        """Return whether proxy rotation can be used."""
        return settings.proxy_rotation_enabled and bool(self._proxies)

    @property
    def last_proxy_host(self) -> str | None:
        """Host/IP used for the most recent proxy selection."""
        return self._last_host

    @property
    def last_proxy_identity(self) -> str | None:
        """Stable identity for the most recent proxy selection."""
        return self._last_identity

    @property
    def active_sku_key(self) -> str | None:
        """SKU scope currently bound to ``_sku_proxy``."""
        return self._sku_key

    def _record_selection(self, endpoint: ProxyEndpoint, index: int) -> ProxyEndpoint:
        self._last_index = index
        self._last_identity = endpoint.identity
        self._last_host = endpoint.host
        return endpoint

    def _pick_strict_next(self) -> ProxyEndpoint:
        """Return the next proxy, never the same index as the previous pick when possible."""
        assert self._proxies
        if len(self._proxies) == 1:
            return self._record_selection(self._proxies[0], 0)

        if self._last_index is None:
            return self._record_selection(self._proxies[0], 0)

        next_index = (self._last_index + 1) % len(self._proxies)
        return self._record_selection(self._proxies[next_index], next_index)

    def begin_sku(self, sku: str, brand: str = "") -> ProxyEndpoint | None:
        """Bind one proxy IP to a SKU; advance rotation only when the SKU changes."""
        if not self.enabled:
            return None

        key = sku_scope_key(sku, brand)
        with self._lock:
            if self._sku_key == key and self._sku_proxy is not None:
                return self._sku_proxy

            use_affinity = settings.proxy_affinity_enabled and not settings.proxy_strict_alternation
            if use_affinity:
                if key not in self._affinity:
                    self._affinity[key] = self._pick_strict_next()
                endpoint = self._affinity[key]
            else:
                endpoint = self._pick_strict_next()

            self._sku_key = key
            self._sku_proxy = endpoint
            logger.info(
                "Proxy bound to SKU",
                sku=sku,
                brand=brand or "",
                sku_scope=key,
                proxy_host=endpoint.host,
                proxy_identity=endpoint.identity,
            )
            return endpoint

    def clear_sku(self) -> None:
        """Release the active SKU proxy scope after all sites finish."""
        with self._lock:
            self._sku_key = None
            self._sku_proxy = None

    def proxy_for_current_scope(self, site_id: str = "") -> ProxyEndpoint | None:
        """Return the proxy for the active SKU scope, or pick one for standalone scripts."""
        if not self.enabled:
            return None

        with self._lock:
            if self._sku_proxy is not None:
                return self._sku_proxy
            return self._select_without_sku_scope(site_id)

    def select_proxy_for_search(self, site_id: str = "") -> ProxyEndpoint | None:
        """Backward-compatible alias for ``proxy_for_current_scope``."""
        return self.proxy_for_current_scope(site_id)

    def _select_without_sku_scope(self, site_id: str = "") -> ProxyEndpoint | None:
        use_affinity = settings.proxy_affinity_enabled and not settings.proxy_strict_alternation
        if use_affinity and site_id:
            if site_id not in self._affinity:
                self._affinity[site_id] = self._pick_strict_next()
            endpoint = self._affinity[site_id]
            index = self._proxies.index(endpoint)
            return self._record_selection(endpoint, index)
        return self._pick_strict_next()

    def next_proxy(self) -> ProxyEndpoint | None:
        """Return the next proxy endpoint (strict alternation)."""
        if not self.enabled:
            return None
        with self._lock:
            return self._pick_strict_next()

    def proxy_for_site(self, site_id: str) -> ProxyEndpoint | None:
        """Backward-compatible alias."""
        return self.proxy_for_current_scope(site_id)


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
