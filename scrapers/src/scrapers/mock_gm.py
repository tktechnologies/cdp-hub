"""Mock GM scraper for E2E testing without real credentials.

Returns realistic fake data, no browser needed.
Easy to remove: delete this file + references in __init__.py and config.py.
"""

import asyncio
import random
import time
from datetime import UTC, datetime

import structlog

from src.models.schemas import (
    Currency,
    ItemCondition,
    PartResult,
    SiteId,
    SiteResult,
)
from src.scrapers.base import BaseScraper

logger = structlog.get_logger()

_MOCK_CATALOG: dict[str, dict] = {
    "93338835": {
        "raw_title": "Filtro de oleo do motor",
        "price": 45.90,
        "availability": "Em estoque",
        "origin": "Brasil",
    },
    "52102242": {
        "raw_title": "Pastilha de freio dianteira",
        "price": 189.50,
        "availability": "Em estoque",
        "origin": "Brasil",
    },
    "24578331": {
        "raw_title": "Correia do alternador",
        "price": 78.30,
        "availability": "Sob encomenda - 3 dias",
        "origin": "Brasil",
    },
    "94703032": {
        "raw_title": "Amortecedor dianteiro",
        "price": 320.00,
        "availability": "Em estoque",
        "origin": "Brasil",
    },
    # Used by interview demo when MOCK_SCRAPERS=true (mirrors field-guide probe SKU).
    "22781768": {
        "raw_title": "Peça GM — preço demo (mock)",
        "price": 412.90,
        "availability": "Em estoque",
        "origin": "Brasil",
    },
}


class MockGMScraper(BaseScraper):
    """Mock scraper returning fake GM parts data. No browser required."""

    @property
    def site_id(self) -> SiteId:
        return SiteId.GM

    @property
    def site_name(self) -> str:
        return "GM Parts Dealer (Mock)"

    async def initialize(self) -> None:
        logger.info("MockGMScraper initialized (no browser)")

    async def shutdown(self) -> None:
        logger.info("MockGMScraper shut down")

    async def login(self, page) -> bool:  # type: ignore[override]
        return True

    async def search_sku(self, page, sku: str, brand: str = "") -> list[PartResult]:  # type: ignore[override]
        return []

    async def scrape_sku(self, sku: str, brand: str = "") -> SiteResult:
        """Return mock results without a browser."""
        start = time.monotonic()
        normalized = self._normalize_sku(sku, brand)

        await asyncio.sleep(random.uniform(0.05, 0.2))

        entry = _MOCK_CATALOG.get(normalized)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if entry:
            result = PartResult(
                sku_searched=sku,
                sku_found=normalized,
                exact_match=True,
                site=self.site_id,
                site_name=self.site_name,
                price=entry["price"],
                currency=Currency.BRL,
                condition=ItemCondition.NEW,
                availability=entry["availability"],
                origin=entry["origin"],
                raw_title=entry["raw_title"],
                scraped_at=datetime.now(UTC),
            )
            logger.info("Mock search", sku=sku, found=True, elapsed_ms=elapsed_ms)
            return SiteResult(
                site=self.site_id,
                site_name=self.site_name,
                status="success",
                results=[result],
                search_time_ms=elapsed_ms,
            )

        logger.info("Mock search", sku=sku, found=False, elapsed_ms=elapsed_ms)
        return SiteResult(
            site=self.site_id,
            site_name=self.site_name,
            status="not_found",
            results=[],
            search_time_ms=elapsed_ms,
        )
