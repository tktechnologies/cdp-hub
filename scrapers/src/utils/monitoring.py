"""Prometheus metrics and health check utilities."""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from prometheus_client import Counter, Gauge, Histogram, generate_latest

logger = structlog.get_logger()

# ─── Prometheus Metrics ────────────────────────────────────────
scrape_requests_total = Counter(
    "cdp_scrape_requests_total",
    "Total scrape requests",
    ["site", "status"],
)

scrape_duration_seconds = Histogram(
    "cdp_scrape_duration_seconds",
    "Time spent scraping per SKU per site",
    ["site"],
    buckets=[1, 5, 10, 15, 30, 60, 120],
)

active_jobs_gauge = Gauge(
    "cdp_active_jobs",
    "Number of currently running scraping jobs",
)

session_health_gauge = Gauge(
    "cdp_session_healthy",
    "Whether a site session is healthy (1) or not (0)",
    ["site"],
)

scrape_cache_hit_total = Counter(
    "cdp_scrape_cache_hit_total",
    "Scrape cache hits (Redis or PostgreSQL warm path)",
    ["source"],
)

scrape_cache_miss_total = Counter(
    "cdp_scrape_cache_miss_total",
    "Scrape cache misses (no entry; live scrape may follow)",
)

# ─── Startup time tracking ────────────────────────────────────
_start_time: float = 0.0


def record_start() -> None:
    """Record application start time."""
    global _start_time
    _start_time = time.monotonic()


def get_uptime_seconds() -> float:
    """Get seconds since application start."""
    if _start_time == 0.0:
        return 0.0
    return time.monotonic() - _start_time


def get_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    return generate_latest()


@asynccontextmanager
async def track_scrape(site: str) -> AsyncGenerator[None, None]:
    """Context manager to track scrape duration and status."""
    start = time.monotonic()
    try:
        yield
        scrape_requests_total.labels(site=site, status="success").inc()
    except Exception:
        scrape_requests_total.labels(site=site, status="error").inc()
        raise
    finally:
        duration = time.monotonic() - start
        scrape_duration_seconds.labels(site=site).observe(duration)
