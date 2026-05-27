"""FastAPI route modules for the scraper API."""

from fastapi import APIRouter

from src.api.routes import dispatch_runs, health, jobs, lookup

router = APIRouter()
router.include_router(jobs.router)
router.include_router(lookup.router)
router.include_router(dispatch_runs.router)
router.include_router(health.router)

__all__ = ["router"]
