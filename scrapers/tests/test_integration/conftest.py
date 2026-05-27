"""Integration test fixtures — mock scrapers + in-memory SQLite."""

import os

os.environ["MOCK_SCRAPERS"] = "true"
os.environ["API_KEY"] = "test-key"

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.models.database import Base
from src.scrapers import _active_scrapers


@pytest.fixture(autouse=True)
async def setup_test_db(monkeypatch):
    """Fresh in-memory SQLite DB for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///", echo=False)
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


@pytest.fixture
def api_headers():
    return {"X-API-Key": "test-key"}
