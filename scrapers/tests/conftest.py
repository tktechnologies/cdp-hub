"""Test configuration and shared fixtures."""

import os

os.environ["JOB_EXECUTION_BACKEND"] = "local"
os.environ.setdefault("SCRAPE_CACHE_ENABLED", "false")
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite+aiosqlite:////tmp/cdp_scraper_pytest_{os.getpid()}.db",
)
os.environ.setdefault(
    "DATABASE_URL_SYNC",
    f"sqlite:////tmp/cdp_scraper_pytest_{os.getpid()}.db",
)

from unittest.mock import AsyncMock, MagicMock

import pytest
import uvloop

from src.models.schemas import (
    Currency,
    ItemCondition,
    PartResult,
    ScrapeJobRequest,
    SiteId,
    SiteResult,
    SKUItem,
)


@pytest.fixture(scope="session")
def event_loop_policy():
    return uvloop.EventLoopPolicy()


@pytest.fixture
def sample_sku_items() -> list[SKUItem]:
    return [
        SKUItem(sku="A0001234567", brand="Mercedes", description="Brake pad"),
        SKUItem(sku="93338835", brand="GM", description="Oil filter"),
        SKUItem(sku="5U0807217BGRU", brand="VW", description="Bumper"),
    ]


@pytest.fixture
def all_sites() -> list[SiteId]:
    return [SiteId.GM, SiteId.MERCADO_LIVRE, SiteId.VW, SiteId.EUROPE]


@pytest.fixture
def sample_part_result() -> PartResult:
    return PartResult(
        sku_searched="93338835",
        sku_found="93338835",
        exact_match=True,
        site=SiteId.GM,
        site_name="GM Parts Dealer",
        price=150.50,
        currency=Currency.BRL,
        condition=ItemCondition.NEW,
        availability="in_stock",
        origin="Brasil",
    )


@pytest.fixture
def sample_site_result(sample_part_result: PartResult) -> SiteResult:
    return SiteResult(
        site=SiteId.GM,
        site_name="GM Parts Dealer",
        status="success",
        results=[sample_part_result],
        search_time_ms=1500,
    )


@pytest.fixture
def sample_job_request() -> ScrapeJobRequest:
    return ScrapeJobRequest(
        items=[
            SKUItem(sku="93338835", brand="GM"),
            SKUItem(sku="A0001234567", brand="Mercedes"),
        ],
        sites=[SiteId.GM, SiteId.MERCADO_LIVRE],
        callback_url="http://localhost:5678/webhook/callback",
    )


@pytest.fixture
def mock_page() -> MagicMock:
    """Mock Playwright Page object."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.fill = AsyncMock()
    page.click = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.query_selector = AsyncMock(return_value=None)
    page.query_selector_all = AsyncMock(return_value=[])
    page.screenshot = AsyncMock()
    page.close = AsyncMock()
    page.keyboard = MagicMock()
    page.keyboard.press = AsyncMock()
    return page
