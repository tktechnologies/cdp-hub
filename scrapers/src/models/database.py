"""SQLAlchemy ORM models for persistent storage."""

from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.pool import NullPool

from src.config import settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


class ScrapeJob(Base):
    """A batch scraping job containing multiple SKU lookups."""

    __tablename__ = "scrape_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status = Column(String(20), nullable=False, default="pending")
    sites = Column(JSON, nullable=False, default=list)
    total_items = Column(Integer, nullable=False, default=0)
    items_succeeded = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    items_processed = Column(Integer, default=0)
    callback_url = Column(Text, nullable=True)
    priority = Column(Integer, default=5)
    errors = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, default=0)
    metadata_ = Column("metadata", JSON, nullable=True)

    items = relationship("ScrapeItem", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_scrape_jobs_status_created_at", "status", "created_at"),)


class DispatchRun(Base):
    """Tracks a dual-pipeline dispatch (scraper + StokAPI) for status polling.

    Redis key convention (reserved): dispatch:run:{id} — see src/redis_keys.py.
    """

    __tablename__ = "dispatch_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    batch_group_id = Column(Text, nullable=False, index=True)
    chat_id = Column(Text, nullable=True, index=True)
    command_route = Column(Text, nullable=True)
    scraper_job_ids = Column(JSON, nullable=False, default=list)
    stokapi_job_id = Column(Text, nullable=True)
    total_skus = Column(Integer, nullable=False, default=0)
    dispatched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    estimated_seconds = Column(Integer, nullable=True)
    scraper_status = Column(String(20), nullable=False, default="pending")
    stokapi_status = Column(String(20), nullable=False, default="pending")
    last_progress_pct = Column(Float, nullable=False, default=0.0)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    progress_message_count = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    reply_channel = Column(Text, nullable=True)
    reply_email = Column(Text, nullable=True)
    command_origin = Column(Text, nullable=True)
    progress_enabled = Column(Boolean, nullable=False, default=True)
    delivery_mode = Column(String(32), nullable=False, default="legacy")
    sheet_row_numbers = Column(JSON, nullable=False, default=list)
    scraper_summary = Column(JSON, nullable=True)
    stokapi_summary = Column(JSON, nullable=True)
    scraper_completed_at = Column(DateTime(timezone=True), nullable=True)
    stokapi_completed_at = Column(DateTime(timezone=True), nullable=True)
    final_notification_status = Column(String(32), nullable=True)
    final_notified_at = Column(DateTime(timezone=True), nullable=True)
    final_notification_attempts = Column(Integer, nullable=False, default=0)
    final_channel = Column(String(20), nullable=True)
    final_error = Column(Text, nullable=True)


class ScrapeItem(Base):
    """Individual SKU lookup within a job."""

    __tablename__ = "scrape_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id = Column(String(36), ForeignKey("scrape_jobs.id"), nullable=False)
    sku = Column(String(100), nullable=False, index=True)
    brand = Column(String(100), default="")
    description = Column(Text, default="")
    status = Column(String(20), default="pending")
    site_results = Column(JSON, default=list)

    job = relationship("ScrapeJob", back_populates="items")
    results = relationship("PartResultRecord", back_populates="item", cascade="all, delete-orphan")


class PartResultRecord(Base):
    """Persisted part search result."""

    __tablename__ = "part_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    item_id = Column(String(36), ForeignKey("scrape_items.id"), nullable=False)
    sku_searched = Column(String(100), nullable=False, index=True)
    sku_found = Column(String(100), nullable=False)
    exact_match = Column(Boolean, default=False)
    site = Column(String(20), nullable=False)
    site_name = Column(String(100), default="")
    price = Column(Float, nullable=True)
    currency = Column(String(3), default="BRL")
    condition = Column(String(20), default="unknown")
    availability = Column(String(50), default="unknown")
    seller_name = Column(String(200), default="")
    seller_uf = Column(String(2), default="")
    seller_company_name = Column(String(200), default="")
    seller_cnpj = Column(String(14), default="")
    product_url = Column(Text, default="")
    origin = Column(String(50), default="")
    raw_title = Column(Text, default="")
    scraped_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    item = relationship("ScrapeItem", back_populates="results")


class SessionState(Base):
    """Track browser session health per site."""

    __tablename__ = "session_states"

    site = Column(String(20), primary_key=True)
    is_valid = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    last_success = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    state_file_path = Column(Text, nullable=True)


# ─── Database Engine ──────────────────────────────────────────────


def normalize_asyncpg_url(database_url: str) -> tuple[str, dict[str, object]]:
    """Move asyncpg SSL URL flags into connect_args where asyncpg expects them."""
    parsed = urlsplit(database_url)
    if parsed.scheme != "postgresql+asyncpg":
        return database_url, {}

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    ssl_value = query.pop("ssl", query.pop("sslmode", None))
    if ssl_value is None:
        return database_url, {}

    normalized_url = urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query),
            parsed.fragment,
        )
    )
    connect_args: dict[str, object] = {}
    if ssl_value.lower() not in {"disable", "false", "0", "off"}:
        connect_args["ssl"] = True
    return normalized_url, connect_args


def build_engine_options(database_url: str, job_execution_backend: str) -> dict[str, object]:
    """Build SQLAlchemy async engine options for API and worker processes."""
    options: dict[str, object] = {"echo": False}
    _normalized_url, connect_args = normalize_asyncpg_url(database_url)
    if connect_args:
        options["connect_args"] = connect_args

    if database_url.startswith("sqlite"):
        return options

    if job_execution_backend == "celery":
        # Celery runs tasks in worker child processes and this code executes each
        # task through asyncio.run(). Avoid reusing asyncpg connections across
        # process/event-loop boundaries.
        options["poolclass"] = NullPool
        return options

    options.update({"pool_size": 5, "max_overflow": 10})
    return options


engine_url, engine_connect_args = normalize_asyncpg_url(settings.database_url)
engine_options = build_engine_options(settings.database_url, settings.job_execution_backend)
if engine_connect_args:
    engine_options["connect_args"] = engine_connect_args

engine = create_async_engine(engine_url, **engine_options)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    """Dependency for FastAPI — yields an async session."""
    async with async_session() as session:
        yield session
