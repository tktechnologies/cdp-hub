from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import JobNotFoundError
from app.db.models import MuvstokJob, MuvstokJobItem
from app.domain.job_status import CallbackStatus, JobItemStatus, JobStatus
from app.schemas.requests import CreateMuvstokJobRequest
from app.schemas.responses import JobItemResponse, JobStatusResponse


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_job(
        self,
        request: CreateMuvstokJobRequest,
        api_client_id: str,
        batch_size: int,
    ) -> MuvstokJob:
        correlation_id = str(uuid4())
        job = MuvstokJob(
            correlation_id=correlation_id,
            api_client_id=api_client_id,
            status=JobStatus.PENDING,
            submitted_sku_count=len(request.skus),
            callback_url=str(request.callback_url),
            idempotency_key=request.idempotency_key,
            metadata_json=request.metadata,
        )
        self._session.add(job)
        await self._session.flush()

        for start in range(0, len(request.skus), batch_size):
            sku_batch = request.skus[start : start + batch_size]
            await self._session.execute(
                insert(MuvstokJobItem),
                [
                    {
                        "id": uuid4(),
                        "job_id": job.id,
                        "correlation_id": correlation_id,
                        "sku": sku,
                        "status": JobItemStatus.PENDING,
                        "attempts": 0,
                        "metadata_json": {},
                    }
                    for sku in sku_batch
                ],
            )
            await self._session.flush()

        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def get_by_idempotency_key(
        self,
        api_client_id: str,
        idempotency_key: str,
    ) -> MuvstokJob | None:
        result = await self._session.execute(
            select(MuvstokJob).where(
                MuvstokJob.api_client_id == api_client_id,
                MuvstokJob.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def mark_queued(self, job_id: UUID) -> MuvstokJob:
        job = await self.get_job_model(job_id)
        job.status = JobStatus.QUEUED
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def get_job_model(self, job_id: UUID) -> MuvstokJob:
        result = await self._session.execute(select(MuvstokJob).where(MuvstokJob.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            raise JobNotFoundError(f"Job {job_id} was not found.")
        return job

    async def mark_processing(self, job_id: UUID) -> MuvstokJob:
        job = await self.get_job_model(job_id)
        job.status = JobStatus.PROCESSING
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def list_actionable_items(self, job_id: UUID) -> list[MuvstokJobItem]:
        result = await self._session.execute(
            select(MuvstokJobItem)
            .where(
                MuvstokJobItem.job_id == job_id,
                MuvstokJobItem.status.in_(
                    (JobItemStatus.PENDING, JobItemStatus.RETRYING, JobItemStatus.PROCESSING)
                ),
            )
            .order_by(MuvstokJobItem.created_at, MuvstokJobItem.sku)
        )
        return list(result.scalars().all())

    async def mark_item_processing(self, item_id: UUID) -> MuvstokJobItem:
        result = await self._session.execute(
            select(MuvstokJobItem).where(MuvstokJobItem.id == item_id)
        )
        item = result.scalar_one()
        item.status = JobItemStatus.PROCESSING
        item.attempts += 1
        await self._session.flush()
        return item

    async def mark_item_succeeded(self, item_id: UUID) -> MuvstokJobItem:
        result = await self._session.execute(
            select(MuvstokJobItem).where(MuvstokJobItem.id == item_id)
        )
        item = result.scalar_one()
        item.status = JobItemStatus.SUCCEEDED
        item.last_error_code = None
        await self._session.flush()
        return item

    async def mark_item_failed(self, item_id: UUID, error_code: str) -> MuvstokJobItem:
        result = await self._session.execute(
            select(MuvstokJobItem).where(MuvstokJobItem.id == item_id)
        )
        item = result.scalar_one()
        item.status = JobItemStatus.FAILED
        item.last_error_code = error_code
        await self._session.flush()
        return item

    async def recount_job_items(self, job_id: UUID) -> tuple[int, int]:
        result = await self._session.execute(
            select(MuvstokJobItem.status).where(MuvstokJobItem.job_id == job_id)
        )
        statuses = list(result.scalars().all())
        succeeded = sum(1 for status in statuses if status == JobItemStatus.SUCCEEDED)
        failed = sum(1 for status in statuses if status == JobItemStatus.FAILED)
        return succeeded, failed

    async def finalize_job(
        self,
        job_id: UUID,
        *,
        status: JobStatus,
        callback_status: CallbackStatus | None,
        succeeded_sku_count: int,
        failed_sku_count: int,
    ) -> MuvstokJob:
        job = await self.get_job_model(job_id)
        job.status = status
        job.succeeded_sku_count = succeeded_sku_count
        job.failed_sku_count = failed_sku_count
        job.callback_status = callback_status
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def set_callback_status(self, job_id: UUID, status: CallbackStatus) -> None:
        await self._session.execute(
            update(MuvstokJob)
            .where(MuvstokJob.id == job_id)
            .values(callback_status=status)
        )
        await self._session.commit()

    async def get_job_status(
        self,
        job_id: UUID,
        items_limit: int,
        items_offset: int,
    ) -> JobStatusResponse:
        job = await self.get_job_model(job_id)
        items_result = await self._session.execute(
            select(MuvstokJobItem)
            .where(MuvstokJobItem.job_id == job_id)
            .order_by(MuvstokJobItem.created_at, MuvstokJobItem.sku)
            .limit(items_limit)
            .offset(items_offset)
        )
        items = list(items_result.scalars().all())

        succeeded = job.succeeded_sku_count
        failed = job.failed_sku_count
        processed: int | None = None
        progress_pct: float | None = None
        estimated_seconds_remaining: int | None = None

        if job.status == JobStatus.PROCESSING:
            succeeded, failed = await self.recount_job_items(job_id)
            processed = succeeded + failed
            total = job.submitted_sku_count
            if total > 0:
                progress_pct = round(processed / total * 100, 1)
            if processed > 0 and job.updated_at:
                elapsed = (datetime.now(UTC) - job.updated_at).total_seconds()
                remaining_items = total - processed
                if remaining_items > 0:
                    estimated_seconds_remaining = int(
                        elapsed / processed * remaining_items
                    )
                else:
                    estimated_seconds_remaining = 0

        return JobStatusResponse(
            job_id=job.id,
            correlation_id=job.correlation_id,
            status=job.status,
            submitted_sku_count=job.submitted_sku_count,
            succeeded_sku_count=succeeded,
            failed_sku_count=failed,
            processed_sku_count=processed,
            progress_pct=progress_pct,
            estimated_seconds_remaining=estimated_seconds_remaining,
            callback_status=job.callback_status.value if job.callback_status else None,
            items=[
                JobItemResponse(
                    sku=item.sku,
                    status=item.status,
                    attempts=item.attempts,
                    last_error_code=item.last_error_code,
                )
                for item in items
            ],
            items_limit=items_limit,
            items_offset=items_offset,
            items_returned=len(items),
            metadata=job.metadata_json,
            created_at=job.created_at or datetime.now(UTC),
            updated_at=job.updated_at or datetime.now(UTC),
        )
