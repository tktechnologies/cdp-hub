"""Job and demo job endpoints."""

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_request_id, verify_api_key
from src.api.errors import APIHTTPException
from src.models.schemas import (
    ScrapeJobRequest,
    ScrapeJobResponse,
    ScrapeJobResult,
    TelegramDemoJobRequest,
    TelegramDemoJobResponse,
)
from src.services import telegram_demo
from src.services.orchestrator import orchestrator

router = APIRouter(tags=["jobs"])


@router.post(
    "/jobs",
    response_model=ScrapeJobResponse,
    dependencies=[Depends(verify_api_key), Depends(get_request_id)],
)
async def create_job(request: ScrapeJobRequest) -> ScrapeJobResponse:
    """Submit a batch scraping job.

    The job runs asynchronously. Use GET /jobs/{job_id} to check status.
    Optionally provide a callback_url for notification on completion.
    """
    try:
        return await orchestrator.submit_job(request)
    except Exception as exc:
        raise APIHTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "service_unavailable",
            f"Unable to queue scraping job: {exc}",
        ) from exc


@router.post(
    "/demo/telegram",
    response_model=TelegramDemoJobResponse,
    dependencies=[Depends(verify_api_key), Depends(get_request_id)],
)
async def create_telegram_demo_job(request: TelegramDemoJobRequest) -> TelegramDemoJobResponse:
    """Submit a small demo job and route completion results to a Telegram chat via n8n."""
    try:
        return await telegram_demo.submit_telegram_demo_job(request)
    except telegram_demo.MissingDemoCallbackUrlError as exc:
        raise APIHTTPException(
            status.HTTP_400_BAD_REQUEST,
            "bad_request",
            "Missing demo callback URL",
        ) from exc


@router.get(
    "/jobs/{job_id}",
    response_model=ScrapeJobResult,
    dependencies=[Depends(verify_api_key), Depends(get_request_id)],
)
async def get_job(job_id: str) -> ScrapeJobResult:
    """Get job status and results."""
    result = await orchestrator.get_job_status(job_id)
    if not result:
        raise APIHTTPException(
            status.HTTP_404_NOT_FOUND,
            "not_found",
            f"Job {job_id} not found",
        )
    return result
