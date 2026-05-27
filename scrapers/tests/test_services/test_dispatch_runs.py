"""Tests for dispatch run registry."""

import os

os.environ.setdefault("MOCK_SCRAPERS", "true")
os.environ.setdefault("API_KEY", "test-key")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.models.database import Base
from src.models.schemas import DispatchRunUpsertRequest
from src.services import dispatch_runs


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    import src.models.database as db_mod
    import src.services.dispatch_runs as dispatch_runs_mod

    monkeypatch.setattr(db_mod, "engine", engine)
    monkeypatch.setattr(db_mod, "async_session", session_factory)
    monkeypatch.setattr(dispatch_runs_mod, "async_session", session_factory)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_upsert_and_list_active_dispatch_run():
    created = await dispatch_runs.upsert_dispatch_run(
        DispatchRunUpsertRequest(
            batch_group_id="bg-test-1",
            chat_id="12345",
            scraper_job_ids=["job-a"],
            stokapi_job_id="job-b",
            total_skus=10,
        )
    )
    assert created.batch_group_id == "bg-test-1"
    assert created.scraper_job_ids == ["job-a"]

    active = await dispatch_runs.list_active_dispatch_runs()
    assert len(active) == 1
    assert active[0].chat_id == "12345"
