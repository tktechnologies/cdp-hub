"""Registry of dual-pipeline dispatch runs for status polling."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from src.models.database import DispatchRun, async_session
from src.models.schemas import (
    DispatchRunProgressUpdate,
    DispatchRunResponse,
    DispatchRunUpsertRequest,
)


def _to_response(row: DispatchRun) -> DispatchRunResponse:
    return DispatchRunResponse(
        id=row.id,
        batch_group_id=row.batch_group_id,
        chat_id=row.chat_id,
        command_route=row.command_route,
        scraper_job_ids=row.scraper_job_ids or [],
        stokapi_job_id=row.stokapi_job_id,
        total_skus=row.total_skus,
        dispatched_at=row.dispatched_at,
        estimated_seconds=row.estimated_seconds,
        scraper_status=row.scraper_status,
        stokapi_status=row.stokapi_status,
        last_progress_pct=row.last_progress_pct,
        last_notified_at=row.last_notified_at,
        progress_message_count=row.progress_message_count,
        completed_at=row.completed_at,
    )


async def upsert_dispatch_run(request: DispatchRunUpsertRequest) -> DispatchRunResponse:
    """Create or update a dispatch run keyed by batch_group_id."""
    async with async_session() as session:
        result = await session.execute(
            select(DispatchRun).where(DispatchRun.batch_group_id == request.batch_group_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = DispatchRun(
                id=str(uuid4()),
                batch_group_id=request.batch_group_id,
            )
            session.add(row)

        row.chat_id = request.chat_id
        row.command_route = request.command_route
        row.scraper_job_ids = request.scraper_job_ids
        row.stokapi_job_id = request.stokapi_job_id
        row.total_skus = request.total_skus
        row.estimated_seconds = request.estimated_seconds
        if request.dispatched_at:
            row.dispatched_at = request.dispatched_at
        await session.commit()
        await session.refresh(row)
        return _to_response(row)


async def list_active_dispatch_runs() -> list[DispatchRunResponse]:
    """Return non-completed runs (for proactive progress workflow)."""
    async with async_session() as session:
        result = await session.execute(
            select(DispatchRun)
            .where(DispatchRun.completed_at.is_(None))
            .order_by(DispatchRun.dispatched_at.desc())
        )
        return [_to_response(row) for row in result.scalars().all()]


async def get_active_dispatch_run_for_chat(chat_id: str) -> DispatchRunResponse | None:
    async with async_session() as session:
        result = await session.execute(
            select(DispatchRun)
            .where(
                DispatchRun.chat_id == chat_id,
                DispatchRun.completed_at.is_(None),
            )
            .order_by(DispatchRun.dispatched_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return _to_response(row) if row else None


async def update_dispatch_run_progress(
    run_id: str,
    update: DispatchRunProgressUpdate,
) -> DispatchRunResponse | None:
    async with async_session() as session:
        result = await session.execute(select(DispatchRun).where(DispatchRun.id == run_id))
        row = result.scalar_one_or_none()
        if not row:
            return None

        if update.last_progress_pct is not None:
            row.last_progress_pct = update.last_progress_pct
            row.last_notified_at = datetime.now(UTC)
        if update.progress_message_count is not None:
            row.progress_message_count = update.progress_message_count
        if update.scraper_status is not None:
            row.scraper_status = update.scraper_status
        if update.stokapi_status is not None:
            row.stokapi_status = update.stokapi_status
        if update.completed_at is not None:
            row.completed_at = update.completed_at

        await session.commit()
        await session.refresh(row)
        return _to_response(row)
