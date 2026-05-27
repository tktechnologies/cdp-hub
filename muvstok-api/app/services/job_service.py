import logging
from datetime import UTC, datetime
from uuid import UUID

from app.api.dependencies import ApiClientContext
from app.core.config import Settings
from app.core.exceptions import JobLimitExceededError
from app.repositories.job_repository import JobRepository
from app.schemas.requests import CreateMuvstokJobRequest
from app.schemas.responses import JobAcceptedResponse, JobStatusResponse
from app.services.queue_service import QueueService

logger = logging.getLogger("muvstok.jobs")


class JobService:
    def __init__(
        self,
        settings: Settings,
        job_repository: JobRepository,
        queue_service: QueueService | None = None,
    ) -> None:
        self._settings = settings
        self._job_repository = job_repository
        self._queue_service = queue_service

    async def create_job(
        self,
        request: CreateMuvstokJobRequest,
        api_client: ApiClientContext,
    ) -> JobAcceptedResponse:
        if len(request.skus) > self._settings.max_skus_per_job:
            msg = f"Job exceeds maximum SKU count of {self._settings.max_skus_per_job}."
            raise JobLimitExceededError(msg)

        if request.idempotency_key is not None:
            existing_job = await self._job_repository.get_by_idempotency_key(
                api_client_id=api_client.client_id,
                idempotency_key=request.idempotency_key,
            )
            if existing_job is not None:
                logger.info(
                    "job_idempotency_hit",
                    extra={
                        "event_name": "job_idempotency_hit",
                        "service": "muvstok-api",
                        "environment": self._settings.environment,
                        "job_id": str(existing_job.id),
                        "correlation_id": existing_job.correlation_id,
                        "status": existing_job.status.value,
                    },
                )
                return JobAcceptedResponse(
                    job_id=existing_job.id,
                    correlation_id=existing_job.correlation_id,
                    status=existing_job.status,
                    submitted_sku_count=existing_job.submitted_sku_count,
                    queued_at=existing_job.updated_at or datetime.now(UTC),
                )

        job = await self._job_repository.create_job(
            request=request,
            api_client_id=api_client.client_id,
            batch_size=self._settings.job_item_batch_size,
        )
        logger.info(
            "job_created",
            extra={
                "event_name": "job_created",
                "service": "muvstok-api",
                "environment": self._settings.environment,
                "job_id": str(job.id),
                "correlation_id": job.correlation_id,
                "status": job.status.value,
            },
        )
        if self._queue_service is None:
            msg = "Queue service is required to create a job."
            raise RuntimeError(msg)
        await self._queue_service.publish_job(
            job_id=job.id,
            correlation_id=job.correlation_id,
            sku_count=job.submitted_sku_count,
        )
        queued_job = await self._job_repository.mark_queued(job.id)
        logger.info(
            "job_queued",
            extra={
                "event_name": "job_queued",
                "service": "muvstok-api",
                "environment": self._settings.environment,
                "job_id": str(queued_job.id),
                "correlation_id": queued_job.correlation_id,
                "status": queued_job.status.value,
            },
        )
        return JobAcceptedResponse(
            job_id=queued_job.id,
            correlation_id=queued_job.correlation_id,
            status=queued_job.status,
            submitted_sku_count=queued_job.submitted_sku_count,
            queued_at=queued_job.updated_at or datetime.now(UTC),
        )

    async def get_job(
        self,
        job_id: UUID,
        items_limit: int,
        items_offset: int,
    ) -> JobStatusResponse:
        return await self._job_repository.get_job_status(job_id, items_limit, items_offset)

    async def close(self) -> None:
        if self._queue_service is not None:
            await self._queue_service.close()
