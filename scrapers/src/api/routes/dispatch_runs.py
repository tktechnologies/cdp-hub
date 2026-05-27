"""Dual-pipeline dispatch run registry endpoints."""

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_request_id, verify_api_key
from src.api.errors import APIHTTPException
from src.models.schemas import (
    DispatchRunProgressUpdate,
    DispatchRunResponse,
    DispatchRunUpsertRequest,
)
from src.services import dispatch_runs

router = APIRouter(tags=["dispatch-runs"])


@router.post(
    "/dispatch-runs",
    response_model=DispatchRunResponse,
    dependencies=[Depends(verify_api_key), Depends(get_request_id)],
)
async def upsert_dispatch_run(request: DispatchRunUpsertRequest) -> DispatchRunResponse:
    """Register or refresh an active dual-pipeline dispatch run."""
    return await dispatch_runs.upsert_dispatch_run(request)


@router.get(
    "/dispatch-runs/active",
    response_model=list[DispatchRunResponse],
    dependencies=[Depends(verify_api_key), Depends(get_request_id)],
)
async def list_active_dispatch_runs() -> list[DispatchRunResponse]:
    """List dispatch runs that have not completed (for progress polling)."""
    return await dispatch_runs.list_active_dispatch_runs()


@router.get(
    "/dispatch-runs/active/for-chat/{chat_id}",
    response_model=DispatchRunResponse,
    dependencies=[Depends(verify_api_key), Depends(get_request_id)],
)
async def get_active_dispatch_run_for_chat(chat_id: str) -> DispatchRunResponse:
    """Latest active dispatch run for a Telegram chat."""
    result = await dispatch_runs.get_active_dispatch_run_for_chat(chat_id)
    if not result:
        raise APIHTTPException(
            status.HTTP_404_NOT_FOUND,
            "not_found",
            "No active dispatch run for chat",
        )
    return result


@router.patch(
    "/dispatch-runs/{run_id}",
    response_model=DispatchRunResponse,
    dependencies=[Depends(verify_api_key), Depends(get_request_id)],
)
async def patch_dispatch_run(
    run_id: str,
    update: DispatchRunProgressUpdate,
) -> DispatchRunResponse:
    """Update progress notification state for a dispatch run."""
    result = await dispatch_runs.update_dispatch_run_progress(run_id, update)
    if not result:
        raise APIHTTPException(
            status.HTTP_404_NOT_FOUND,
            "not_found",
            f"Dispatch run {run_id} not found",
        )
    return result
