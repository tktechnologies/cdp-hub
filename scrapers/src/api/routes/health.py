"""Service health endpoint."""

from fastapi import APIRouter

from src.models.schemas import HealthResponse
from src.services import health as health_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Service health check endpoint (no auth required)."""
    return await health_service.get_health()
