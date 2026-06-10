"""Standardized API error responses and exception handlers."""

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error: ErrorBody


_STATUS_TO_CODE: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    422: "validation_error",
    status.HTTP_503_SERVICE_UNAVAILABLE: "service_unavailable",
}


def error_payload(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details or {}),
    ).model_dump()


class APIHTTPException(HTTPException):
    """HTTPException that carries a stable machine-readable error code."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.error_code = code
        self.error_details = details or {}


def _message_from_detail(detail: Any) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return "Request validation failed"
    return str(detail)


def _details_from_detail(detail: Any) -> dict[str, Any]:
    if isinstance(detail, list):
        return {"errors": detail}
    return {}


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers that emit the standard ``error`` response envelope."""

    @app.exception_handler(APIHTTPException)
    async def api_http_exception_handler(
        _: Request,
        exc: APIHTTPException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                exc.error_code, _message_from_detail(exc.detail), details=exc.error_details
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc, APIHTTPException):
            return await api_http_exception_handler(_, exc)
        code = _STATUS_TO_CODE.get(exc.status_code, "error")
        message = _message_from_detail(exc.detail)
        details = _details_from_detail(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(code, message, details=details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_payload(
                "validation_error",
                "Request validation failed",
                details={"errors": exc.errors()},
            ),
        )
