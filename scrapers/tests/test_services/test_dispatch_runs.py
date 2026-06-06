"""Tests for dispatch run registry and final notification."""

# ruff: noqa: E402

import os
from uuid import uuid4

os.environ.setdefault("MOCK_SCRAPERS", "true")
os.environ.setdefault("API_KEY", "test-key")
_test_db_path = f"/tmp/cdp_dispatch_pytest_{os.getpid()}_{uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db_path}"
os.environ["DATABASE_URL_SYNC"] = f"sqlite:///{_test_db_path}"

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.models.database import Base
from src.models.schemas import (
    DispatchRunUpsertRequest,
    FinalNotificationPatch,
    PipelineResultRequest,
    PipelineResultSummary,
)
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


def _summary(**kwargs: int | float | str | None) -> PipelineResultSummary:
    return PipelineResultSummary(**kwargs)


@pytest.mark.asyncio
async def test_upsert_stores_recipient_and_progress_flags():
    created = await dispatch_runs.upsert_dispatch_run(
        DispatchRunUpsertRequest(
            batch_group_id="bg-agg-1",
            chat_id="999",
            reply_channel="telegram",
            command_origin="telegram",
            progress_enabled=False,
            delivery_mode="aggregate",
            sheet_row_numbers=[2, 3, 4],
            total_skus=3,
        )
    )
    assert created.delivery_mode == "aggregate"
    assert created.progress_enabled is False
    assert created.sheet_row_numbers == [2, 3, 4]


@pytest.mark.asyncio
async def test_first_pipeline_result_not_ready():
    await dispatch_runs.upsert_dispatch_run(
        DispatchRunUpsertRequest(batch_group_id="bg-pipe-1", total_skus=1)
    )
    resp = await dispatch_runs.record_pipeline_result(
        "bg-pipe-1",
        PipelineResultRequest(
            source="scraper",
            status="completed",
            summary=_summary(with_price=1),
        ),
    )
    assert resp.both_terminal is False
    assert resp.ready_for_final is False
    assert resp.claim is None


@pytest.mark.asyncio
async def test_second_terminal_result_claims_once():
    await dispatch_runs.upsert_dispatch_run(
        DispatchRunUpsertRequest(
            batch_group_id="bg-pipe-2",
            chat_id="111",
            reply_channel="telegram",
            delivery_mode="aggregate",
        )
    )
    await dispatch_runs.record_pipeline_result(
        "bg-pipe-2",
        PipelineResultRequest(
            source="scraper",
            status="completed",
            summary=_summary(with_price=2, no_price=1),
        ),
    )
    second = await dispatch_runs.record_pipeline_result(
        "bg-pipe-2",
        PipelineResultRequest(
            source="stokapi",
            status="succeeded",
            summary=_summary(with_price=1, not_found=1),
        ),
    )
    assert second.both_terminal is True
    assert second.ready_for_final is True
    assert second.claim is not None
    assert second.claim["scraper_summary"]["with_price"] == 2

    duplicate = await dispatch_runs.record_pipeline_result(
        "bg-pipe-2",
        PipelineResultRequest(
            source="stokapi",
            status="succeeded",
            summary=_summary(with_price=99),
        ),
    )
    assert duplicate.already_notified is False
    assert duplicate.ready_for_final is True


@pytest.mark.asyncio
async def test_failed_dispatch_branch_counts_as_terminal():
    await dispatch_runs.upsert_dispatch_run(
        DispatchRunUpsertRequest(batch_group_id="bg-fail-1", reply_channel="email", reply_email="a@b.com")
    )
    await dispatch_runs.record_pipeline_result(
        "bg-fail-1",
        PipelineResultRequest(
            source="scraper",
            status="failed",
            summary=_summary(errors=5, status="failed", failed_reason="dispatch error"),
        ),
    )
    ready = await dispatch_runs.record_pipeline_result(
        "bg-fail-1",
        PipelineResultRequest(
            source="stokapi",
            status="succeeded",
            summary=_summary(with_price=0),
        ),
    )
    assert ready.ready_for_final is True


@pytest.mark.asyncio
async def test_one_finished_branch_never_sends_partial():
    await dispatch_runs.upsert_dispatch_run(
        DispatchRunUpsertRequest(batch_group_id="bg-partial-1", chat_id="222")
    )
    only_scraper = await dispatch_runs.record_pipeline_result(
        "bg-partial-1",
        PipelineResultRequest(
            source="scraper",
            status="completed",
            summary=_summary(with_price=1),
        ),
    )
    assert only_scraper.ready_for_final is False


@pytest.mark.asyncio
async def test_final_notification_patch_sent_and_skipped():
    await dispatch_runs.upsert_dispatch_run(
        DispatchRunUpsertRequest(batch_group_id="bg-final-1", reply_channel="email", reply_email="u@x.com")
    )
    claimed = await dispatch_runs.record_pipeline_result(
        "bg-final-1",
        PipelineResultRequest(source="scraper", status="completed", summary=_summary()),
    )
    await dispatch_runs.record_pipeline_result(
        "bg-final-1",
        PipelineResultRequest(source="stokapi", status="succeeded", summary=_summary()),
    )
    run_id = claimed.run_id
    sent = await dispatch_runs.patch_final_notification(
        run_id,
        FinalNotificationPatch(status="sent", final_channel="email"),
    )
    assert sent is not None
    assert sent.final_notification_status == "sent"

    await dispatch_runs.upsert_dispatch_run(DispatchRunUpsertRequest(batch_group_id="bg-final-2"))
    r2 = await dispatch_runs.record_pipeline_result(
        "bg-final-2",
        PipelineResultRequest(source="scraper", status="completed", summary=_summary()),
    )
    await dispatch_runs.record_pipeline_result(
        "bg-final-2",
        PipelineResultRequest(source="stokapi", status="succeeded", summary=_summary()),
    )
    skipped = await dispatch_runs.patch_final_notification(
        r2.run_id,
        FinalNotificationPatch(status="skipped_no_target"),
    )
    assert skipped.final_notification_status == "skipped_no_target"


@pytest.mark.asyncio
async def test_list_active_skips_progress_disabled():
    await dispatch_runs.upsert_dispatch_run(
        DispatchRunUpsertRequest(
            batch_group_id="bg-prog-1",
            chat_id="333",
            progress_enabled=False,
        )
    )
    active = await dispatch_runs.list_active_dispatch_runs()
    assert active == []
