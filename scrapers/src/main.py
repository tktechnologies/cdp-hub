"""CDP Parts Scraper — FastAPI Application."""

from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.errors import register_exception_handlers
from src.config import settings
from src.models.database import init_db
from src.scrapers import shutdown_all_scrapers
from src.utils.logging_config import setup_logging
from src.utils.monitoring import record_start

# Configure structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown hooks."""
    # Startup
    record_start()
    logger.info("Starting CDP Scraper API", version="0.1.0")
    await init_db()
    settings.browser_state_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Database initialized, browser state directory ready")

    yield

    # Shutdown
    logger.info("Shutting down scrapers...")
    await shutdown_all_scrapers()
    logger.info("Shutdown complete")


app = FastAPI(
    title="CDP Parts Scraper API",
    description=(
        "Automated automotive parts price comparison across multiple supplier websites. "
        "Handles authenticated access, multi-site search, and structured JSON output."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

register_exception_handlers(app)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    """Propagate X-Request-ID on every request/response."""
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,  # Restrict to configured origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
from src.api.routes import router  # noqa: E402

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"service": "cdp-scraper", "version": "0.1.0", "docs": "/docs"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from fastapi.responses import Response

    from src.utils.monitoring import get_metrics

    return Response(content=get_metrics(), media_type="text/plain")
