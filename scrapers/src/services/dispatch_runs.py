"""Registry of dual-pipeline dispatch runs for progress and final notification."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import or_, select, update

from src.models.database import DispatchRun, async_session
from src.models.schemas import (
    DispatchRunProgressUpdate,
    DispatchRunResponse,
    DispatchRunUpsertRequest,
    FinalNotificationPatch,
    PipelineResultRequest,
    PipelineResultResponse,
)

SCRAPER_TERMINAL = frozenset({"completed", "partial", "failed"})
STOKAPI_TERMINAL = frozenset({"succeeded", "partially_succeeded", "failed", "completed"})
FINAL_OPEN = frozenset({None, "", "pending"})
FINAL_CLAIMED = frozenset({"claiming"})


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
        reply_channel=row.reply_channel,
        reply_email=row.reply_email,
        command_origin=row.command_origin,
        progress_enabled=bool(row.progress_enabled),
        delivery_mode=row.delivery_mode or "legacy",
        sheet_row_numbers=row.sheet_row_numbers or [],
        scraper_summary=row.scraper_summary,
        stokapi_summary=row.stokapi_summary,
        scraper_completed_at=row.scraper_completed_at,
        stokapi_completed_at=row.stokapi_completed_at,
        final_notification_status=row.final_notification_status,
        final_notified_at=row.final_notified_at,
        final_notification_attempts=row.final_notification_attempts or 0,
        final_channel=row.final_channel,
        final_error=row.final_error,
    )


def _normalize_status(status: str) -> str:
    return str(status or "").strip().lower()


def _is_scraper_terminal(status: str) -> bool:
    return _normalize_status(status) in SCRAPER_TERMINAL


def _is_stokapi_terminal(status: str) -> bool:
    return _normalize_status(status) in STOKAPI_TERMINAL


def _both_terminal(row: DispatchRun) -> bool:
    return _is_scraper_terminal(row.scraper_status) and _is_stokapi_terminal(row.stokapi_status)


def _has_recipient(row: DispatchRun) -> bool:
    if row.reply_channel == "telegram" and row.chat_id:
        return True
    if row.reply_channel == "email" and row.reply_email:
        return True
    if row.chat_id:
        return True
    return bool(row.reply_email)


def _build_claim(row: DispatchRun) -> dict:
    return {
        "run_id": row.id,
        "batch_group_id": row.batch_group_id,
        "reply_channel": row.reply_channel,
        "reply_email": row.reply_email,
        "chat_id": row.chat_id,
        "command_origin": row.command_origin,
        "command_route": row.command_route,
        "delivery_mode": row.delivery_mode,
        "sheet_row_numbers": row.sheet_row_numbers or [],
        "scraper_summary": row.scraper_summary,
        "stokapi_summary": row.stokapi_summary,
        "total_skus": row.total_skus,
    }


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
        if request.reply_channel is not None:
            row.reply_channel = request.reply_channel
        if request.reply_email is not None:
            row.reply_email = request.reply_email
        if request.command_origin is not None:
            row.command_origin = request.command_origin
        row.progress_enabled = request.progress_enabled
        row.delivery_mode = request.delivery_mode
        if request.sheet_row_numbers:
            row.sheet_row_numbers = request.sheet_row_numbers
        if request.dispatched_at:
            row.dispatched_at = request.dispatched_at
        await session.commit()
        await session.refresh(row)
        return _to_response(row)


async def list_active_dispatch_runs() -> list[DispatchRunResponse]:
    """Return non-completed runs with proactive progress enabled."""
    async with async_session() as session:
        result = await session.execute(
            select(DispatchRun)
            .where(DispatchRun.completed_at.is_(None))
            .where(DispatchRun.progress_enabled.is_(True))
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


async def record_pipeline_result(
    batch_group_id: str,
    request: PipelineResultRequest,
) -> PipelineResultResponse:
    """Store pipeline summary; claim final notification when both arms are terminal."""
    now = datetime.now(UTC)
    source = _normalize_status(request.source)
    status = _normalize_status(request.status)
    summary = request.summary.model_dump(mode="json")

    async with async_session() as session:
        result = await session.execute(
            select(DispatchRun).where(DispatchRun.batch_group_id == batch_group_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = DispatchRun(
                id=str(uuid4()),
                batch_group_id=batch_group_id,
                delivery_mode="aggregate",
                progress_enabled=False,
            )
            session.add(row)

        if source == "scraper":
            row.scraper_summary = summary
            row.scraper_status = status
            row.scraper_completed_at = now
        else:
            row.stokapi_summary = summary
            row.stokapi_status = status
            row.stokapi_completed_at = now

        both_terminal = _both_terminal(row)
        final_status = row.final_notification_status
        already_notified = final_status in ("sent", "skipped_no_target", "failed")

        ready_for_final = False
        claim: dict | None = None

        if both_terminal and not already_notified:
            row.completed_at = row.completed_at or now
            if final_status in FINAL_OPEN:
                claim_result = await session.execute(
                    update(DispatchRun)
                    .where(DispatchRun.id == row.id)
                    .where(
                        or_(
                            DispatchRun.final_notification_status.is_(None),
                            DispatchRun.final_notification_status == "",
                            DispatchRun.final_notification_status == "pending",
                        )
                    )
                    .values(
                        final_notification_status="claiming",
                        final_notification_attempts=(row.final_notification_attempts or 0) + 1,
                    )
                )
                if claim_result.rowcount:
                    await session.refresh(row)
                    ready_for_final = True
                    claim = _build_claim(row)
            elif final_status == "claiming":
                ready_for_final = True
                claim = _build_claim(row)

        await session.commit()
        await session.refresh(row)

        return PipelineResultResponse(
            run_id=row.id,
            batch_group_id=row.batch_group_id,
            both_terminal=both_terminal,
            ready_for_final=ready_for_final,
            already_notified=already_notified,
            claim=claim,
        )


async def list_ready_final_notifications() -> list[DispatchRunResponse]:
    """Runs claimed for final notification but not yet patched as sent/failed."""
    async with async_session() as session:
        result = await session.execute(
            select(DispatchRun).where(DispatchRun.final_notification_status == "claiming")
        )
        return [_to_response(row) for row in result.scalars().all()]


async def patch_final_notification(
    run_id: str,
    patch: FinalNotificationPatch,
) -> DispatchRunResponse | None:
    async with async_session() as session:
        result = await session.execute(select(DispatchRun).where(DispatchRun.id == run_id))
        row = result.scalar_one_or_none()
        if not row:
            return None

        now = datetime.now(UTC)
        row.final_notification_status = patch.status
        row.final_notified_at = now
        row.final_channel = patch.final_channel
        row.final_error = patch.final_error
        row.completed_at = row.completed_at or now

        if patch.status == "skipped_no_target" and not _has_recipient(row):
            pass

        await session.commit()
        await session.refresh(row)
        return _to_response(row)
