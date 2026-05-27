from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.routes import health, jobs
from app.core.config import get_settings
from app.core.exceptions import JobLimitExceededError, JobNotFoundError
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
    )
    application.include_router(health.router)
    application.include_router(jobs.router)

    @application.exception_handler(JobNotFoundError)
    async def job_not_found_handler(_: Request, exc: JobNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @application.exception_handler(JobLimitExceededError)
    async def job_limit_handler(_: Request, exc: JobLimitExceededError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    return application


app = create_app()
