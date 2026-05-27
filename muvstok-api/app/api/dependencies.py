import hashlib
import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass(frozen=True)
class ApiClientContext:
    client_id: str


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


async def get_api_client(
    api_key: str | None = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> ApiClientContext:
    configured_keys = settings.api_key_values
    if not configured_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured.",
        )

    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key.")

    for configured_key in configured_keys:
        if secrets.compare_digest(api_key, configured_key):
            key_fingerprint = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
            return ApiClientContext(client_id=f"configured:{key_fingerprint}")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")
