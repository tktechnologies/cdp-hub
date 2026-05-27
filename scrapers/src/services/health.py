"""Health check assembly for the scraper API."""

from src.models.schemas import HealthResponse
from src.utils.monitoring import get_uptime_seconds


async def get_health() -> HealthResponse:
    """Build the public health payload."""
    return HealthResponse(
        status="ok",
        uptime_seconds=get_uptime_seconds(),
    )
