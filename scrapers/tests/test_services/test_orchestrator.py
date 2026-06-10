"""Tests for the orchestrator service."""

import os

os.environ.setdefault("MOCK_SCRAPERS", "true")
os.environ.setdefault("API_KEY", "test-key")
os.environ["JOB_EXECUTION_BACKEND"] = "local"

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import settings
from src.models.database import Base
from src.models.schemas import (
    Currency,
    JobStatus,
    PartResult,
    ScrapeJobRequest,
    SiteId,
    SiteResult,
    SKUItem,
)
from src.scrapers import _active_scrapers


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db(monkeypatch):
    """Fresh in-memory SQLite DB for each orchestrator test."""
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


class TestOrchestrator:
    """Test orchestrator job management."""

    @pytest.mark.asyncio
    async def test_submit_job_returns_pending(self, sample_job_request, monkeypatch):
        from src.services.orchestrator import Orchestrator

        async def skip_background_job(_self, _job_id, _request):
            return None

        monkeypatch.setattr(Orchestrator, "_execute_job", skip_background_job)

        orch = Orchestrator()
        response = await orch.submit_job(sample_job_request)

        assert response.job_id
        assert response.status == JobStatus.PENDING
        assert response.total_items == 2

    @pytest.mark.asyncio
    async def test_submit_job_estimates_duration(self, sample_job_request, monkeypatch):
        from src.services.orchestrator import Orchestrator

        async def skip_background_job(_self, _job_id, _request):
            return None

        monkeypatch.setattr(Orchestrator, "_execute_job", skip_background_job)

        orch = Orchestrator()
        response = await orch.submit_job(sample_job_request)

        # Conservative default: 2 items, 2 sequential sites (~24s) + inter-SKU delay.
        assert response.estimated_duration_seconds == 62

    @pytest.mark.asyncio
    async def test_submit_job_enqueues_celery_when_configured(
        self, sample_job_request, monkeypatch
    ):
        from src.services.orchestrator import Orchestrator

        queued: dict[str, object] = {}

        def fake_delay(job_id: str, payload: dict[str, object]) -> None:
            queued["job_id"] = job_id
            queued["payload"] = payload

        async def fail_if_local_execution_runs(_self, _job_id, _request):
            raise AssertionError("local execution should not run for Celery backend")

        monkeypatch.setattr(settings, "job_execution_backend", "celery")
        monkeypatch.setattr(
            "src.tasks.scrape_jobs.execute_scrape_job.delay",
            fake_delay,
        )
        monkeypatch.setattr(Orchestrator, "_execute_job", fail_if_local_execution_runs)

        orch = Orchestrator()
        response = await orch.submit_job(sample_job_request)

        assert queued["job_id"] == response.job_id
        assert queued["payload"]["items"][0]["sku"] == "93338835"
        assert response.status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_nonexistent_job_returns_none(self):
        from src.services.orchestrator import Orchestrator

        orch = Orchestrator()
        result = await orch.get_job_status("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_job_status_preserves_persisted_site_statuses(self, monkeypatch):
        from src.models.database import ScrapeJob, async_session
        from src.services.orchestrator import Orchestrator

        job_id = "site-status-job"
        request = ScrapeJobRequest(
            items=[SKUItem(sku="93338835", brand="GM")],
            sites=[SiteId.GM, SiteId.MERCADO_LIVRE, SiteId.MELIBOX],
        )

        async with async_session() as session:
            session.add(
                ScrapeJob(
                    id=job_id,
                    status=JobStatus.PENDING.value,
                    sites=[site.value for site in request.sites],
                    total_items=1,
                )
            )
            await session.commit()

        class FakeScraper:
            def __init__(self, result: SiteResult) -> None:
                self.result = result

            async def scrape_sku(self, _sku: str, _brand: str = "") -> SiteResult:
                return self.result

        site_results = {
            SiteId.GM: SiteResult(
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
                        availability="in_stock",
                        origin="Brasil",
                    )
                ],
                search_time_ms=100,
            ),
            SiteId.MERCADO_LIVRE: SiteResult(
                site=SiteId.MERCADO_LIVRE,
                site_name="Mercado Livre",
                status="not_found",
                results=[],
                search_time_ms=200,
            ),
            SiteId.MELIBOX: SiteResult(
                site=SiteId.MELIBOX,
                site_name="Melibox",
                status="error",
                error_message="blocked",
                results=[],
                search_time_ms=300,
            ),
        }

        async def fake_get_scraper(site_id: SiteId) -> FakeScraper:
            return FakeScraper(site_results[site_id])

        monkeypatch.setattr("src.services.orchestrator.get_scraper", fake_get_scraper)

        orch = Orchestrator()
        await orch.execute_queued_job(job_id, request)

        result = await orch.get_job_status(job_id)

        assert result is not None
        assert result.results[0].total_results == 1
        assert result.sku_success_count == 1
        assert result.sku_any_hit_pct == 100
        assert result.all_sites_not_found_count == 0
        assert result.warning_messages == ["93338835 / Melibox: blocked"]
        statuses = {
            site_result.site: site_result.status for site_result in result.results[0].site_results
        }
        assert statuses == {
            SiteId.GM: "success",
            SiteId.MERCADO_LIVRE: "not_found",
            SiteId.MELIBOX: "error",
        }
        blocked = next(
            site_result
            for site_result in result.results[0].site_results
            if site_result.site == SiteId.MELIBOX
        )
        assert blocked.error_message == "blocked"

    @pytest.mark.asyncio
    async def test_goparts_scraper_is_registered_and_invoked(self, monkeypatch):
        from src.services.orchestrator import Orchestrator

        class FakeGoParts:
            async def scrape_sku(self, sku: str, brand: str = ""):
                from src.models.schemas import SiteId, SiteResult

                return SiteResult(
                    site=SiteId.GOPARTS,
                    site_name="GoParts Brazil",
                    status="not_found",
                    proxy_host="20.1.2.3",
                )

        async def fake_get_scraper(site_id):
            assert site_id == SiteId.GOPARTS
            return FakeGoParts()

        monkeypatch.setattr(
            "src.services.orchestrator.get_scraper",
            fake_get_scraper,
        )

        result = await Orchestrator()._scrape_one_site(
            SiteId.GOPARTS,
            SKUItem(sku="ABC123", brand=""),
        )

        assert result.status == "not_found"
        assert result.proxy_host == "20.1.2.3"
