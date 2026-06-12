"""Tests for Redis scrape result cache."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.models.database import Base
from src.models.schemas import (
    Currency,
    ItemCondition,
    PartResult,
    ScrapeJobRequest,
    SiteId,
    SiteResult,
    SKUItem,
)
from src.scrapers import _active_scrapers
from src.services.scrape_cache import (
    ScrapeCacheService,
    build_cache_key,
    normalize_cache_sku,
    normalize_redis_tls_url,
)
from src.utils.monitoring import scrape_cache_hit_total, scrape_cache_miss_total


@pytest.fixture
def sample_site_result() -> SiteResult:
    return SiteResult(
        site=SiteId.GM,
        site_name="GM",
        status="success",
        results=[
            PartResult(
                sku_searched="93338835",
                sku_found="93338835",
                exact_match=True,
                site=SiteId.GM,
                site_name="GM",
                price=150.0,
                currency=Currency.BRL,
                condition=ItemCondition.NEW,
                availability="in_stock",
                seller_name="Dealer Center",
                seller_uf="PR",
                seller_company_name="Dealer Center Ltda",
                seller_cnpj="05788992000187",
                origin="Brasil",
            )
        ],
        search_time_ms=100,
    )


class TestCacheKeyHelpers:
    def test_normalize_cache_sku_strips_separators(self):
        assert normalize_cache_sku("A-000.1234/567") == "A0001234567"

    def test_mercedes_eu_rule(self):
        assert (
            normalize_cache_sku("A0001234567", brand="Mercedes", site_id=SiteId.EUROPE)
            == "0001234567"
        )

    def test_build_cache_key_includes_site(self):
        key = build_cache_key("93338835", "GM", SiteId.GM)
        assert key.startswith("scrape:v1:gm:")
        assert "93338835" in key

    def test_normalize_redis_tls_url_strips_legacy_cert_query(self):
        url, kwargs = normalize_redis_tls_url(
            "rediss://:secret@example.redis.cache.windows.net:6380/1?ssl_cert_reqs=CERT_NONE"
        )
        assert url == "rediss://:secret@example.redis.cache.windows.net:6380/1"
        assert kwargs == {"ssl_cert_reqs": "none"}

    def test_normalize_redis_tls_url_preserves_other_query_values(self):
        url, kwargs = normalize_redis_tls_url(
            "rediss://:secret@example.redis.cache.windows.net:6380/1?foo=bar&ssl_cert_reqs=CERT_NONE"
        )
        assert url == "rediss://:secret@example.redis.cache.windows.net:6380/1?foo=bar"
        assert kwargs == {"ssl_cert_reqs": "none"}


class TestScrapeCacheService:
    def test_ttl_for_status(self):
        service = ScrapeCacheService()
        assert service._ttl_for_status("success") == 86400
        assert service._ttl_for_status("not_found") == 86400
        assert service._ttl_for_status("blocked") == 86400
        assert service._ttl_for_status("error") is None

    @pytest.mark.asyncio
    async def test_set_and_get_round_trip(self, sample_site_result, monkeypatch):
        store: dict[str, str] = {}
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=lambda key: store.get(key))
        mock_redis.setex = AsyncMock(
            side_effect=lambda key, _ttl, value: store.__setitem__(key, value)
        )

        monkeypatch.setattr("src.services.scrape_cache.settings.scrape_cache_enabled", True)
        monkeypatch.setattr("src.services.scrape_cache.settings.scrape_cache_pg_fallback", False)

        service = ScrapeCacheService()
        service._client = mock_redis

        await service.set_site_result("93338835", "GM", sample_site_result)
        cached = await service.get_site_result("93338835", "GM", SiteId.GM)

        assert cached is not None
        assert cached.from_cache is True
        assert cached.search_time_ms == 0
        assert cached.status == "success"
        assert cached.results[0].price == 150.0
        assert cached.results[0].seller_uf == "PR"
        assert cached.results[0].seller_company_name == "Dealer Center Ltda"
        assert cached.results[0].seller_cnpj == "05788992000187"
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_status_not_cached(self, monkeypatch):
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.setex = AsyncMock()

        monkeypatch.setattr("src.services.scrape_cache.settings.scrape_cache_enabled", True)
        monkeypatch.setattr("src.services.scrape_cache.settings.scrape_cache_pg_fallback", False)

        service = ScrapeCacheService()
        service._client = mock_redis

        await service.set_site_result(
            "X",
            "",
            SiteResult(site=SiteId.VW, site_name="VW", status="error", error_message="fail"),
        )
        mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_site_result_records_hit_and_miss_metrics(
        self, sample_site_result, monkeypatch
    ):
        store: dict[str, str] = {}
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=lambda key: store.get(key))
        mock_redis.setex = AsyncMock(
            side_effect=lambda key, _ttl, value: store.__setitem__(key, value)
        )

        monkeypatch.setattr("src.services.scrape_cache.settings.scrape_cache_enabled", True)
        monkeypatch.setattr("src.services.scrape_cache.settings.scrape_cache_pg_fallback", False)

        service = ScrapeCacheService()
        service._client = mock_redis

        redis_hits_before = scrape_cache_hit_total.labels(source="redis")._value.get()
        misses_before = scrape_cache_miss_total._value.get()

        miss = await service.get_site_result("93338835", "GM", SiteId.GM)
        assert miss is None
        assert scrape_cache_miss_total._value.get() == misses_before + 1

        await service.set_site_result("93338835", "GM", sample_site_result)
        hit = await service.get_site_result("93338835", "GM", SiteId.GM)
        assert hit is not None
        assert scrape_cache_hit_total.labels(source="redis")._value.get() == redis_hits_before + 1


class TestOrchestratorCacheIntegration:
    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_db(self, monkeypatch):
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        import src.models.database as db_mod

        monkeypatch.setattr(db_mod, "engine", engine)
        monkeypatch.setattr(db_mod, "async_session", session_factory)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        _active_scrapers.clear()
        yield
        _active_scrapers.clear()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_cache_hit_skips_live_scrape(self, monkeypatch):
        from src.models.database import ScrapeJob, async_session
        from src.services.orchestrator import Orchestrator

        monkeypatch.setattr("src.services.scrape_cache.settings.scrape_cache_enabled", True)

        cached = SiteResult(
            site=SiteId.GM,
            site_name="GM",
            status="success",
            from_cache=True,
            cached_at=datetime.now(UTC),
            results=[
                PartResult(
                    sku_searched="93338835",
                    sku_found="93338835",
                    exact_match=True,
                    site=SiteId.GM,
                    site_name="GM",
                    price=99.0,
                    currency=Currency.BRL,
                    availability="in_stock",
                    origin="Brasil",
                )
            ],
        )

        get_mock = AsyncMock(return_value=cached)
        set_mock = AsyncMock()
        scrape_mock = AsyncMock()

        monkeypatch.setattr("src.services.scrape_cache.scrape_cache.get_site_result", get_mock)
        monkeypatch.setattr("src.services.scrape_cache.scrape_cache.set_site_result", set_mock)
        monkeypatch.setattr("src.services.orchestrator.get_scraper", scrape_mock)

        job_id = "cache-hit-job"
        request = ScrapeJobRequest(
            items=[SKUItem(sku="93338835", brand="GM")],
            sites=[SiteId.GM],
        )

        async with async_session() as session:
            session.add(
                ScrapeJob(
                    id=job_id,
                    status="pending",
                    sites=["gm"],
                    total_items=1,
                )
            )
            await session.commit()

        orch = Orchestrator()
        await orch.execute_queued_job(job_id, request)

        get_mock.assert_called_once()
        scrape_mock.assert_not_called()
        set_mock.assert_not_called()

        result = await orch.get_job_status(job_id)
        assert result is not None
        assert result.results[0].cache_hits == 1
        assert result.results[0].live_scrapes == 0
        assert result.results[0].site_results[0].from_cache is True

    @pytest.mark.asyncio
    async def test_lookup_sku_cache_hit(self, monkeypatch):
        from src.services.orchestrator import Orchestrator

        monkeypatch.setattr("src.services.scrape_cache.settings.scrape_cache_enabled", True)

        cached = SiteResult(
            site=SiteId.GM,
            site_name="GM",
            status="success",
            from_cache=True,
            cached_at=datetime.now(UTC),
            search_time_ms=9999,
            results=[
                PartResult(
                    sku_searched="93338835",
                    sku_found="93338835",
                    exact_match=True,
                    site=SiteId.GM,
                    site_name="GM",
                    price=99.0,
                    currency=Currency.BRL,
                    availability="in_stock",
                    origin="Brasil",
                )
            ],
        )

        monkeypatch.setattr(
            "src.services.scrape_cache.scrape_cache.get_site_result",
            AsyncMock(return_value=cached),
        )
        monkeypatch.setattr(
            "src.services.orchestrator.get_scraper",
            AsyncMock(),
        )

        result = await Orchestrator().lookup_sku("93338835", "GM", [SiteId.GM])
        assert result.cache_hits == 1
        assert result.live_scrapes == 0
        assert result.site_results[0].from_cache is True
        assert result.site_results[0].search_time_ms == 0
