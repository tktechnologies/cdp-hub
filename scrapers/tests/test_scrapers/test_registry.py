"""Tests for scraper registry mock fallback logic."""

import pytest

from src.models.schemas import SiteId
from src.scrapers import (
    ARCHIVED_SCRAPER_REGISTRY,
    SCRAPER_REGISTRY,
    _active_scrapers,
    _should_use_mock,
)
from src.scrapers.melibox import MeliboxScraper
from src.scrapers.mock_gm import MockGMScraper


class TestRegistryFallback:
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        _active_scrapers.clear()
        yield
        _active_scrapers.clear()

    def test_mock_when_env_set(self, monkeypatch):
        monkeypatch.setattr("src.scrapers.settings.mock_scrapers", True)
        assert _should_use_mock(SiteId.GM) is True

    def test_no_mock_when_no_credentials_for_public_gm(self, monkeypatch):
        monkeypatch.setattr("src.scrapers.settings.mock_scrapers", False)
        monkeypatch.setattr("src.scrapers.settings.credential_gm_user", "")
        monkeypatch.setattr("src.scrapers.settings.credential_gm_pass", "")
        assert _should_use_mock(SiteId.GM) is False

    def test_no_mock_when_credentials_present(self, monkeypatch):
        monkeypatch.setattr("src.scrapers.settings.mock_scrapers", False)
        monkeypatch.setattr("src.scrapers.settings.credential_gm_user", "user")
        monkeypatch.setattr("src.scrapers.settings.credential_gm_pass", "pass")
        assert _should_use_mock(SiteId.GM) is False

    def test_no_mock_for_unimplemented_sites(self, monkeypatch):
        monkeypatch.setattr("src.scrapers.settings.mock_scrapers", True)
        assert _should_use_mock(SiteId.VW) is False

    def test_melibox_registered(self):
        assert SCRAPER_REGISTRY[SiteId.MELIBOX] is MeliboxScraper

    def test_all_production_sites_registered(self):
        assert set(SCRAPER_REGISTRY) == {
            SiteId.GM,
            SiteId.MERCADO_LIVRE,
            SiteId.VW,
            SiteId.EUROPE,
            SiteId.PECA_DIRETA,
            SiteId.MELIBOX,
        }

    def test_blocked_sites_are_archived(self):
        assert set(ARCHIVED_SCRAPER_REGISTRY) == {
            SiteId.GOPARTS,
            SiteId.PROCURA_PECAS,
            SiteId.EBAY,
        }

    @pytest.mark.asyncio
    async def test_get_scraper_returns_mock(self, monkeypatch):
        monkeypatch.setattr("src.scrapers.settings.mock_scrapers", True)
        from src.scrapers import get_scraper

        scraper = await get_scraper(SiteId.GM)
        assert isinstance(scraper, MockGMScraper)
