"""Tests for BaseScraper SKU normalization logic."""

from unittest.mock import AsyncMock, MagicMock

from src.config import settings
from src.models.schemas import SiteId
from src.scrapers.base import BaseScraper
from src.utils.proxy_manager import ProxyEndpoint


class ConcreteScraper(BaseScraper):
    def __init__(self, site_id: SiteId = SiteId.GM) -> None:
        super().__init__()
        self._site_id = site_id

    @property
    def site_id(self):
        return self._site_id

    @property
    def site_name(self):
        return "Test"

    async def login(self, page):
        return True

    async def search_sku(self, page, sku, brand=""):
        return []


class TestSKUNormalization:
    """Test _normalize_sku with various business rules."""

    def _make_scraper(self, site_id: SiteId) -> BaseScraper:
        """Create a minimal concrete scraper for testing."""
        return ConcreteScraper(site_id)

    def test_strips_spaces(self):
        scraper = self._make_scraper(SiteId.GM)
        assert scraper._normalize_sku("A000 123 4567") == "A0001234567"

    def test_strips_hyphens(self):
        scraper = self._make_scraper(SiteId.GM)
        assert scraper._normalize_sku("A000-1234-567") == "A0001234567"

    def test_strips_dots(self):
        scraper = self._make_scraper(SiteId.GM)
        assert scraper._normalize_sku("A000.1234.567") == "A0001234567"

    def test_uppercases(self):
        scraper = self._make_scraper(SiteId.GM)
        assert scraper._normalize_sku("a0001234567") == "A0001234567"

    def test_mercedes_eu_removes_first_char(self):
        scraper = self._make_scraper(SiteId.EUROPE)
        result = scraper._normalize_sku("A0001234567", brand="Mercedes")
        assert result == "0001234567"

    def test_mercedes_non_eu_keeps_first_char(self):
        scraper = self._make_scraper(SiteId.GM)
        result = scraper._normalize_sku("A0001234567", brand="Mercedes")
        assert result == "A0001234567"

    def test_non_mercedes_eu_keeps_first_char(self):
        scraper = self._make_scraper(SiteId.EUROPE)
        result = scraper._normalize_sku("A0001234567", brand="VW")
        assert result == "A0001234567"

    def test_mercedes_mb_alias(self):
        scraper = self._make_scraper(SiteId.EUROPE)
        result = scraper._normalize_sku("A0001234567", brand="MB")
        assert result == "0001234567"

    def test_mercedes_benz_full_name(self):
        scraper = self._make_scraper(SiteId.EUROPE)
        result = scraper._normalize_sku("A0001234567", brand="Mercedes-Benz")
        assert result == "0001234567"


def test_default_user_agent_uses_chromium_major_version(monkeypatch):
    monkeypatch.setattr(settings, "browser_user_agents", [])

    user_agent = ConcreteScraper()._select_user_agent("140.0.7339.16")

    assert "X11; Linux x86_64" in user_agent
    assert "Chrome/140.0.0.0" in user_agent


def test_configured_user_agent_pool_is_used(monkeypatch):
    monkeypatch.setattr(settings, "browser_user_agents", ["  ", "UA-A", "UA-B"])
    monkeypatch.setattr("src.scrapers.base.random.choice", lambda choices: choices[0])

    assert ConcreteScraper()._select_user_agent("140.0") == "UA-A"


def test_context_options_include_browser_profile(monkeypatch):
    monkeypatch.setattr(settings, "browser_locale", "pt-BR")
    monkeypatch.setattr(settings, "browser_timezone_id", "America/Sao_Paulo")
    monkeypatch.setattr(settings, "browser_accept_language", "pt-BR,pt;q=0.9")
    monkeypatch.setattr(settings, "browser_viewport_width", 1366)
    monkeypatch.setattr(settings, "browser_viewport_height", 768)
    monkeypatch.setattr(settings, "browser_extra_http_headers_enabled", True)
    monkeypatch.setattr(settings, "browser_user_agents", [])

    options = ConcreteScraper()._build_context_options("140.0.7339.16")

    assert options["viewport"] == {"width": 1366, "height": 768}
    assert options["screen"] == {"width": 1366, "height": 768}
    assert options["locale"] == "pt-BR"
    assert options["timezone_id"] == "America/Sao_Paulo"
    assert options["user_agent"].startswith("Mozilla/5.0")
    assert options["extra_http_headers"] == {"Accept-Language": "pt-BR,pt;q=0.9"}


def test_state_file_includes_proxy_identity_when_enabled(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "browser_state_dir", tmp_path)
    monkeypatch.setattr(settings, "proxy_rotation_enabled", True)
    monkeypatch.setattr(settings, "proxy_state_per_identity", True)
    scraper = ConcreteScraper(SiteId.MERCADO_LIVRE)
    proxy = ProxyEndpoint.from_url("http://user:pass@20.1.2.3:3128")
    scraper._proxy_identity = proxy.identity

    assert scraper.state_file == tmp_path / f"ml_{proxy.identity}_state.json"


def test_httpx_proxy_url_uses_current_proxy() -> None:
    scraper = ConcreteScraper()
    scraper._proxy_endpoint = ProxyEndpoint.from_url("http://user:pass@20.1.2.3:3128")

    assert scraper._httpx_proxy_url() == "http://user:pass@20.1.2.3:3128"


class FakeRequest:
    def __init__(self, *, navigation: bool, resource_type: str = "document") -> None:
        self._navigation = navigation
        self.resource_type = resource_type

    def is_navigation_request(self) -> bool:
        return self._navigation


class FakeResponse:
    def __init__(self, *, status: int, request: FakeRequest) -> None:
        self.status = status
        self.request = request
        self.url = "https://example.com/blocked"


class FakeObservedPage:
    def __init__(self) -> None:
        self.handlers = {}

    def on(self, event_name, handler) -> None:
        self.handlers[event_name] = handler


def test_response_observer_records_navigation_403(monkeypatch):
    monkeypatch.setattr(settings, "anti_bot_block_status_codes", [403, 429])
    scraper = ConcreteScraper()
    page = FakeObservedPage()

    scraper._attach_anti_bot_observers(page)
    page.handlers["response"](FakeResponse(status=403, request=FakeRequest(navigation=True)))

    assert scraper._last_http_block == {
        "status": 403,
        "url": "https://example.com/blocked",
    }


async def test_session_recheck_skips_repeated_probes(monkeypatch):
    monkeypatch.setattr(settings, "session_recheck_seconds", 900)
    scraper = ConcreteScraper()
    scraper._is_session_valid = AsyncMock(return_value=True)  # type: ignore[method-assign]
    page = MagicMock()

    assert await scraper.ensure_authenticated(page) is True
    assert await scraper.ensure_authenticated(page) is True
    scraper._is_session_valid.assert_awaited_once()


def test_response_observer_ignores_asset_403(monkeypatch):
    monkeypatch.setattr(settings, "anti_bot_block_status_codes", [403, 429])
    scraper = ConcreteScraper()
    page = FakeObservedPage()

    scraper._attach_anti_bot_observers(page)
    page.handlers["response"](
        FakeResponse(status=403, request=FakeRequest(navigation=False, resource_type="image"))
    )

    assert scraper._last_http_block is None
