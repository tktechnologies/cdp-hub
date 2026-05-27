from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import ApiClientContext, get_api_client, get_db_session
from app.clients.redis_queue_client import RedisQueueClient
from app.core.config import Settings, get_settings
from app.repositories.job_repository import JobRepository
from app.repositories.queue_repository import QueueRepository
from app.schemas.requests import CreateMuvstokJobRequest
from app.schemas.responses import JobAcceptedResponse, JobStatusResponse
from app.services.job_service import JobService
from app.services.queue_service import QueueService

router = APIRouter(prefix="/api/v1/muvstok/jobs", tags=["jobs"])

# TODO(platform-phase-3): PATCH /jobs/{job_id} parity with scraper dispatch-runs progress
# updates if n8n needs in-flight job mutation on this service.


def build_job_service(session: AsyncSession, settings: Settings, with_queue: bool) -> JobService:
    job_repository = JobRepository(session)
    if not with_queue:
        return JobService(settings, job_repository)

    queue_repository = QueueRepository(session)
    queue_client = RedisQueueClient(settings)
    queue_service = QueueService(queue_client, queue_repository)
    return JobService(settings, job_repository, queue_service)


@router.post("", response_model=JobAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    request: CreateMuvstokJobRequest,
    api_client: ApiClientContext = Depends(get_api_client),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> JobAcceptedResponse:
    service = build_job_service(session, settings, with_queue=True)
    try:
        return await service.create_job(request, api_client)
    finally:
        await service.close()


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: UUID,
    items_limit: int = Query(default=100, ge=0, le=1000),
    items_offset: int = Query(default=0, ge=0),
    _: ApiClientContext = Depends(get_api_client),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> JobStatusResponse:
    service = build_job_service(session, settings, with_queue=False)
    return await service.get_job(job_id, items_limit, items_offset)
