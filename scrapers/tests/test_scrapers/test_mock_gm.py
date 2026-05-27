"""Tests for MockGMScraper."""

import pytest

from src.models.schemas import SiteId
from src.scrapers.mock_gm import MockGMScraper


class TestMockGMScraper:
    @pytest.mark.asyncio
    async def test_known_sku_returns_success(self):
        scraper = MockGMScraper()
        await scraper.initialize()
        result = await scraper.scrape_sku("93338835", brand="GM")
        assert result.status == "success"
        assert len(result.results) == 1
        assert result.results[0].price == 45.90
        assert result.results[0].exact_match is True
        assert result.results[0].origin == "Brasil"
        await scraper.shutdown()

    @pytest.mark.asyncio
    async def test_unknown_sku_returns_not_found(self):
        scraper = MockGMScraper()
        await scraper.initialize()
        result = await scraper.scrape_sku("NONEXISTENT")
        assert result.status == "not_found"
        assert len(result.results) == 0
        await scraper.shutdown()

    @pytest.mark.asyncio
    async def test_sku_normalization_strips_hyphens(self):
        scraper = MockGMScraper()
        await scraper.initialize()
        result = await scraper.scrape_sku("933-388-35")
        assert result.status == "success"
        await scraper.shutdown()

    def test_site_id(self):
        assert MockGMScraper().site_id == SiteId.GM

    def test_site_name_indicates_mock(self):
        assert "Mock" in MockGMScraper().site_name
