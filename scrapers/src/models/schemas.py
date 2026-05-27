"""Pydantic models for API request/response schemas and internal data transfer."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SiteId(StrEnum):
    """Supported scraping target sites."""
    GM = "gm"
    MERCADO_LIVRE = "ml"
    VW = "vw"
    EUROPE = "eu"
    GOPARTS = "goparts"
    PROCURA_PECAS = "procurapecas"
    PECA_DIRETA = "pecadireta"
    EBAY = "ebay"
    MELIBOX = "melibox"


class Currency(StrEnum):
    BRL = "BRL"
    USD = "USD"
    EUR = "EUR"


class ItemCondition(StrEnum):
    NEW = "new"
    USED = "used"
    UNKNOWN = "unknown"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some sites succeeded, some failed


# ─── Request Models ───────────────────────────────────────────────

class SKUItem(BaseModel):
    """Single SKU to search across sites."""
    sku: str = Field(..., description="Part SKU code to search", examples=["A0001234567"])
    brand: str = Field(default="", description="Part brand (e.g., Mercedes, GM, VW)")
    description: str = Field(default="", description="Optional part description")


class ScrapeJobRequest(BaseModel):
    """Request to start a new scraping job."""
    items: list[SKUItem] = Field(..., min_length=1, max_length=500)
    sites: list[SiteId] = Field(
        default=[
            SiteId.GM,
            SiteId.MERCADO_LIVRE,
            SiteId.VW,
            SiteId.EUROPE,
            SiteId.PECA_DIRETA,
        ],
        description=(
            "Which active sites to search. Melibox requires login and is explicit-only. "
            "GoParts, Procura Peças, and eBay are archived and not included in defaults."
        )
    )
    callback_url: str | None = Field(
        default=None,
        description="Webhook URL to POST results when job completes"
    )
    priority: int = Field(default=5, ge=1, le=10, description="Job priority 1-10 (10=highest)")
    force_refresh: bool = Field(
        default=False,
        description="When true, skip Redis/PostgreSQL cache and run live scrapers",
    )
    batch_group_id: str | None = Field(
        default=None,
        description="Correlates scraper + StokAPI jobs dispatched together",
    )
    chat_id: str | None = Field(
        default=None,
        description="Telegram chat that triggered the job (for status lookups)",
    )
    command_route: str | None = Field(
        default=None,
        description="Telegram command that triggered the job (e.g. .analisar, .sku)",
    )


class TelegramDemoJobRequest(BaseModel):
    """Meeting/demo helper request that sends completion results to Telegram via n8n."""
    chat_id: str = Field(..., description="Telegram chat ID that should receive the result message")
    items: list[SKUItem] = Field(..., min_length=1, max_length=3)
    sites: list[SiteId] = Field(
        default=[SiteId.GM, SiteId.MERCADO_LIVRE, SiteId.VW],
        description="Small site set for a fast visible demo",
    )
    callback_url: str | None = Field(
        default=None,
        description="Override the n8n result webhook URL. Defaults to DEMO_CALLBACK_URL.",
    )
    priority: int = Field(default=8, ge=1, le=10)
    ad_hoc: bool = True


class InterviewDemoRequest(BaseModel):
    """Start the local headed interview demo from a remote automation flow."""
    chat_id: str = Field(..., description="Telegram chat ID requesting the demo")
    sites: str = Field(default="gm,ml,vw", description="Comma-separated demo site IDs")
    timeout_seconds: float = Field(default=180.0, ge=30.0, le=600.0)
    headless: bool = Field(default=False)


class SingleSKURequest(BaseModel):
    """Quick single-SKU lookup (synchronous)."""
    sku: str
    brand: str = ""
    sites: list[SiteId] = Field(default=[SiteId.GM, SiteId.MERCADO_LIVRE, SiteId.VW])
    force_refresh: bool = Field(
        default=False,
        description="When true, skip Redis/PostgreSQL cache and run live scrapers",
    )


# ─── Response Models ──────────────────────────────────────────────

class PartResult(BaseModel):
    """Single part result from one site."""
    sku_searched: str
    sku_found: str
    exact_match: bool
    site: SiteId
    site_name: str = Field(description="Human-readable site name")
    price: float | None = None
    currency: Currency = Currency.BRL
    condition: ItemCondition = ItemCondition.UNKNOWN
    availability: str = Field(default="unknown", description="In stock, out of stock, etc.")
    seller_name: str = ""
    product_url: str = ""
    origin: str = Field(default="", description="Origin region: Brasil, Europa, EUA, China")
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    raw_title: str = Field(default="", description="Original listing title from the site")


class SiteResult(BaseModel):
    """Aggregated results from one site for one SKU."""
    site: SiteId
    site_name: str
    status: str = Field(description="success, not_found, no_price, blocked, error, timeout")
    error_message: str = ""
    results: list[PartResult] = []
    search_time_ms: int = 0
    from_cache: bool = Field(
        default=False,
        description="True when this site result was served from Redis or PostgreSQL cache",
    )
    cached_at: datetime | None = Field(
        default=None,
        description="When the cached snapshot was originally scraped",
    )


class SKUResult(BaseModel):
    """All results for a single SKU across all searched sites."""
    sku: str
    brand: str = ""
    site_results: list[SiteResult] = []
    best_price: PartResult | None = None
    total_results: int = 0
    cache_hits: int = Field(default=0, description="Sites served from cache without live scrape")
    live_scrapes: int = Field(default=0, description="Sites that ran a live scraper this request")


class ScrapeJobResponse(BaseModel):
    """Response after creating a scraping job."""
    job_id: str
    status: JobStatus
    total_items: int
    sites: list[SiteId]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    estimated_duration_seconds: int = 0


class TelegramDemoJobResponse(ScrapeJobResponse):
    """Response for demo jobs routed back to Telegram."""
    callback_url: str
    telegram_chat_id: str


class InterviewDemoStartResponse(BaseModel):
    """Response returned immediately after starting an interview demo."""
    demo_id: str
    status: str
    telegram_chat_id: str
    status_url: str


class InterviewDemoStatusResponse(BaseModel):
    """Current status and summary of a local interview demo run."""
    demo_id: str
    status: str
    telegram_chat_id: str
    started_at: datetime
    completed_at: datetime | None = None
    return_code: int | None = None
    sites: str
    output_path: str
    summary_text: str = ""
    error_message: str = ""


class ScrapeJobResult(BaseModel):
    """Full job result with all SKU results."""
    job_id: str
    status: JobStatus
    results: list[SKUResult] = []
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float = 0
    total_items: int = 0
    items_succeeded: int = 0
    items_failed: int = 0
    items_processed: int = 0
    progress_pct: float = 0
    estimated_seconds_remaining: int | None = None
    errors: list[str] = []
    sku_success_count: int = 0
    sku_any_hit_pct: float = 0
    all_sites_not_found_count: int = 0
    warning_messages: list[str] = []


# ─── Dispatch run registry (dual pipeline progress) ─────────────

class DispatchRunUpsertRequest(BaseModel):
    """Register or refresh an active dual-pipeline run."""

    batch_group_id: str
    chat_id: str | None = None
    command_route: str | None = None
    scraper_job_ids: list[str] = Field(default_factory=list)
    stokapi_job_id: str | None = None
    total_skus: int = 0
    estimated_seconds: int | None = None
    dispatched_at: datetime | None = None


class DispatchRunResponse(BaseModel):
    """Active or historical dispatch run."""

    id: str
    batch_group_id: str
    chat_id: str | None = None
    command_route: str | None = None
    scraper_job_ids: list[str] = Field(default_factory=list)
    stokapi_job_id: str | None = None
    total_skus: int = 0
    dispatched_at: datetime
    estimated_seconds: int | None = None
    scraper_status: str = "pending"
    stokapi_status: str = "pending"
    last_progress_pct: float = 0
    last_notified_at: datetime | None = None
    progress_message_count: int = 0
    completed_at: datetime | None = None


class DispatchRunProgressUpdate(BaseModel):
    """Update progress notification state for a run."""

    last_progress_pct: float | None = None
    progress_message_count: int | None = None
    scraper_status: str | None = None
    stokapi_status: str | None = None
    completed_at: datetime | None = None


# ─── Health & Monitoring ──────────────────────────────────────────

class SiteHealth(BaseModel):
    site: SiteId
    status: str  # "healthy", "degraded", "down"
    last_successful_scrape: datetime | None = None
    session_valid: bool = False
    error_rate_24h: float = 0.0


class HealthResponse(BaseModel):
    status: str  # "ok", "degraded", "down"
    version: str = "0.1.0"
    sites: list[SiteHealth] = []
    active_jobs: int = 0
    uptime_seconds: float = 0
