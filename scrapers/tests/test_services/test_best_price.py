"""Tests for best-price aggregation rules."""

from src.models.schemas import Currency, PartResult, SiteId, SiteResult, SKUItem
from src.services.orchestrator import Orchestrator
from src.services.result_formatter import _find_best_price


def _part(price: float, currency: Currency, site: SiteId = SiteId.GM) -> PartResult:
    return PartResult(
        sku_searched="93338835",
        sku_found="93338835",
        exact_match=True,
        site=site,
        site_name=site.value,
        price=price,
        currency=currency,
        availability="in_stock",
        origin="Brasil",
    )


def test_best_price_is_lowest_when_currency_matches():
    best = _find_best_price([
        _part(150.0, Currency.BRL),
        _part(99.0, Currency.BRL, SiteId.MERCADO_LIVRE),
    ])

    assert best is not None
    assert best.price == 99.0
    assert best.currency == Currency.BRL


def test_best_price_is_empty_when_currencies_are_mixed():
    best = _find_best_price([
        _part(150.0, Currency.BRL),
        _part(20.0, Currency.USD, SiteId.EUROPE),
    ])

    assert best is None


async def test_orchestrator_does_not_compare_mixed_currencies(monkeypatch):
    class FakeScraper:
        def __init__(self, result: SiteResult) -> None:
            self.result = result

        async def scrape_sku(self, sku: str, brand: str = "") -> SiteResult:
            return self.result

    site_results = {
        SiteId.GM: SiteResult(
            site=SiteId.GM,
            site_name="gm",
            status="success",
            results=[_part(150.0, Currency.BRL)],
        ),
        SiteId.EUROPE: SiteResult(
            site=SiteId.EUROPE,
            site_name="eu",
            status="success",
            results=[_part(20.0, Currency.USD, SiteId.EUROPE)],
        ),
    }

    async def fake_get_scraper(site_id: SiteId) -> FakeScraper:
        return FakeScraper(site_results[site_id])

    monkeypatch.setattr("src.services.orchestrator.get_scraper", fake_get_scraper)

    result = await Orchestrator()._search_sku_all_sites(
        SKUItem(sku="93338835", brand="GM"),
        [SiteId.GM, SiteId.EUROPE],
    )

    assert result.best_price is None
    assert result.total_results == 2
