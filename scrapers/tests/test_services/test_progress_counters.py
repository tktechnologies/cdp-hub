"""Tests for incremental job progress counters."""

import os

os.environ.setdefault("MOCK_SCRAPERS", "true")
os.environ.setdefault("API_KEY", "test-key")
os.environ["JOB_EXECUTION_BACKEND"] = "local"

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import src.models.database as db_mod
from src.models.database import Base, ScrapeJob
from src.models.schemas import JobStatus, ScrapeJobRequest, SiteId, SKUItem
from src.services.orchestrator import Orchestrator


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    import src.models.database as db_mod

    monkeypatch.setattr(db_mod, "engine", engine)
    monkeypatch.setattr(db_mod, "async_session", session_factory)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_incremental_items_processed_persisted(monkeypatch):
    async def fake_search(_self, item, sites, *, force_refresh=False):
        from src.models.schemas import SKUResult

        return SKUResult(sku=item.sku, brand=item.brand, total_results=1)

    monkeypatch.setattr(Orchestrator, "_search_sku_all_sites", fake_search)

    orch = Orchestrator()
    request = ScrapeJobRequest(
        items=[SKUItem(sku="SKU00001"), SKUItem(sku="SKU00002")],
        sites=[SiteId.GM],
    )
    job_id = str(uuid4())
    async with db_mod.async_session() as session:
        session.add(
            ScrapeJob(
                id=job_id,
                status=JobStatus.PENDING.value,
                sites=[SiteId.GM.value],
                total_items=2,
            )
        )
        await session.commit()

    await orch.execute_queued_job(job_id, request)

    result = await orch.get_job_status(job_id)
    assert result is not None
    assert result.status in (JobStatus.COMPLETED, JobStatus.PARTIAL)
    assert result.items_processed == 2
    assert result.progress_pct == 100.0

    async with db_mod.async_session() as session:
        db_job = (await session.execute(select(ScrapeJob))).scalar_one()
        assert db_job.items_processed == 2
        assert db_job.items_succeeded == 2
