"""FastAPI dependencies for scraper API routes."""

from uuid import uuid4

from fastapi import Header, Request, status

from src.api.errors import APIHTTPException
from src.config import settings


async def verify_api_key(x_api_key: str | None = Header(default=None)) -> str:
    """Validate API key from the ``X-API-Key`` request header."""
    if x_api_key != settings.api_key:
        raise APIHTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "unauthorized",
            "Invalid API key",
        )
    return x_api_key


async def get_request_id(
    request: Request,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> str:
    """Resolve request ID from header or generate one for this request."""
    request_id = x_request_id or getattr(request.state, "request_id", None) or str(uuid4())
    request.state.request_id = request_id
    return request_id
