from collections.abc import Awaitable
from typing import cast

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/api/v1/muvstok", tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    settings = get_settings()
    payload: dict[str, str] = {
        "status": "ok",
        "service": "api-diversos",
        "redis": "ok",
    }
    try:
        from redis.asyncio import Redis

        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await cast(Awaitable[bool], redis.ping())
        await redis.aclose()
    except Exception:
        payload["status"] = "degraded"
        payload["redis"] = "unavailable"
    return payload
