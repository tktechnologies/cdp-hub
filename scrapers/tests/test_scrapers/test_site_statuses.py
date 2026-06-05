"""Tests for shared scraper site status classification."""

from __future__ import annotations

from src.models.schemas import (
    Currency,
    ItemCondition,
    PartResult,
    SiteId,
    SKUResultStatus,
    SourceHealth,
)
from src.scrapers.base import BaseScraper


class StatusScraper(BaseScraper):
    @property
    def site_id(self) -> SiteId:
        return SiteId.GM

    @property
    def site_name(self) -> str:
        return "Status Test"

    async def login(self, page) -> bool:
        return True

    async def search_sku(self, page, sku: str, brand: str = "") -> list[PartResult]:
        return []


def _part(*, price: float | None, exact_match: bool) -> PartResult:
    return PartResult(
        sku_searched="06K907811B",
        sku_found="06K907811B" if exact_match else "OTHER",
        exact_match=exact_match,
        site=SiteId.GM,
        site_name="Status Test",
        price=price,
        currency=Currency.BRL,
        condition=ItemCondition.NEW,
        availability="in_stock",
        seller_name="",
        product_url="",
        origin="Brasil",
        raw_title="Test part",
    )


def test_success_requires_exact_match_with_positive_price() -> None:
    result = StatusScraper()._site_result_from_search(
        [_part(price=123.45, exact_match=True)],
        elapsed_ms=50,
    )

    assert result.status == "success"
    assert result.results[0].price == 123.45
    assert result.sku_result == SKUResultStatus.FOUND_PRICE
    assert result.source_health == SourceHealth.WORKING
    assert result.has_valid_price is True


def test_no_price_when_exact_product_has_no_positive_price() -> None:
    result = StatusScraper()._site_result_from_search(
        [_part(price=None, exact_match=True), _part(price=0.0, exact_match=True)],
        elapsed_ms=50,
    )

    assert result.status == "no_price"
    assert len(result.results) == 2
    assert result.sku_result == SKUResultStatus.NO_PRICE
    assert result.has_valid_price is False


def test_no_price_when_exact_product_is_out_of_stock() -> None:
    part = _part(price=123.45, exact_match=True)
    part.availability = "Fora de estoque"

    result = StatusScraper()._site_result_from_search([part], elapsed_ms=50)

    assert result.status == "no_price"
    assert result.results[0].availability == "Fora de estoque"
    assert result.sku_result == SKUResultStatus.NO_PRICE


def test_not_found_when_only_non_exact_candidates_are_returned() -> None:
    result = StatusScraper()._site_result_from_search(
        [_part(price=123.45, exact_match=False)],
        elapsed_ms=50,
    )

    assert result.status == "not_found"
    assert result.results == []
    assert result.sku_result == SKUResultStatus.NOT_FOUND
    assert result.has_valid_price is False


def test_not_found_when_no_results_are_returned() -> None:
    result = StatusScraper()._site_result_from_search([], elapsed_ms=50)

    assert result.status == "not_found"
    assert result.results == []
    assert result.sku_result == SKUResultStatus.NOT_FOUND


class FakeBlockedPage:
    async def inner_text(self, selector: str) -> str:
        assert selector == "body"
        return "Access Denied"

    async def query_selector(self, selector: str):
        return None


async def test_detect_blocked_access_denied_page() -> None:
    assert await StatusScraper()._detect_blocked(FakeBlockedPage()) is True
