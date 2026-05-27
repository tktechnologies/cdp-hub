"""Single-SKU lookup endpoint."""

from fastapi import APIRouter, Depends

from src.api.dependencies import get_request_id, verify_api_key
from src.models.schemas import SingleSKURequest, SKUResult
from src.services.orchestrator import orchestrator

router = APIRouter(tags=["lookup"])


@router.post(
    "/lookup",
    response_model=SKUResult,
    dependencies=[Depends(verify_api_key), Depends(get_request_id)],
)
async def quick_lookup(request: SingleSKURequest) -> SKUResult:
    """Synchronous single-SKU lookup across specified sites.

    Runs in the API process with Redis cache (no Celery round-trip).
    For batch processing, use POST /jobs instead.
    """
    return await orchestrator.lookup_sku(
        request.sku,
        request.brand,
        request.sites,
        force_refresh=request.force_refresh,
    )
