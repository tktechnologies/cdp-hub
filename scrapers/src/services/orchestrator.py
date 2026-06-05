"""Orchestration service — coordinates multi-site scraping jobs."""

import asyncio
import random
import time
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import structlog
from sqlalchemy import select

from src.config import settings
from src.models.schemas import (
    JobStatus,
    ScrapeJobRequest,
    ScrapeJobResponse,
    ScrapeJobResult,
    SiteId,
    SiteResult,
    SKUItem,
    SKUResult,
    SKUResultStatus,
    SourceHealth,
)
from src.scrapers import get_scraper
from src.services.result_formatter import _find_best_price
from src.utils.job_estimate import estimate_job_duration_seconds

logger = structlog.get_logger()


class Orchestrator:
    """Coordinates scraping jobs across multiple sites.

    Responsibilities:
    - Accept job requests with lists of SKUs and target sites
    - Fan out searches to multiple scrapers concurrently
    - Aggregate results into unified JSON
    - Track job status and send callbacks to external consumers
    """


    def __init__(self) -> None:
        self._jobs_cache: dict[str, ScrapeJobResult] = {}  # Fast-path cache
        self._job_events: dict[str, asyncio.Event] = {}  # Completion notification
        self._background_tasks: set[asyncio.Task] = set()

    def _apply_summary_metrics(self, job: ScrapeJobResult) -> None:
        """Populate callback-friendly summary fields from typed SKU results."""
        total = job.total_items or len(job.results)

        def has_result_evidence(result: SKUResult) -> bool:
            return result.has_any_exact_evidence

        def has_priced_result(result: SKUResult) -> bool:
            return result.has_valid_price

        priced = sum(1 for result in job.results if has_priced_result(result))
        evidence = sum(1 for result in job.results if has_result_evidence(result))
        no_price = sum(
            1
            for result in job.results
            if result.sku_result == SKUResultStatus.NO_PRICE
        )
        blocked = sum(
            1
            for result in job.results
            if result.blocked_site_count > 0
            and result.sku_result != SKUResultStatus.FOUND_PRICE
        )
        errored = sum(
            1
            for result in job.results
            if result.error_site_count > 0
            and result.sku_result not in (SKUResultStatus.FOUND_PRICE, SKUResultStatus.NO_PRICE)
        )
        all_sites_not_found = 0
        warning_messages: list[str] = []

        for result in job.results:
            site_results = result.site_results
            if site_results and all(
                site_result.status.lower() == "not_found"
                for site_result in site_results
            ):
                all_sites_not_found += 1

            for site_result in site_results:
                status = site_result.status.lower()
                if site_result.source_health in {
                    SourceHealth.BLOCKED,
                    SourceHealth.TIMEOUT,
                    SourceHealth.ERROR,
                }:
                    message = site_result.error_message or status
                    warning_messages.append(
                        f"{result.sku} / {site_result.site_name}: {message}"
                    )

        # Legacy fields stay populated for existing progress consumers. New reporting
        # fields below are the source of truth for "found price" dashboards.
        job.sku_success_count = evidence
        job.sku_any_hit_pct = (evidence / total * 100) if total else 0
        job.all_sites_not_found_count = all_sites_not_found
        job.warning_messages = warning_messages
        job.priced_sku_count = priced
        job.any_evidence_sku_count = evidence
        job.no_price_sku_count = no_price
        job.blocked_sku_count = blocked
        job.error_sku_count = errored

    async def submit_job(self, request: ScrapeJobRequest) -> ScrapeJobResponse:
        """Create and queue a new scraping job."""
        from src.models.database import ScrapeJob, async_session

        job_id = str(uuid4())

        estimated_duration = estimate_job_duration_seconds(
            len(request.items),
            len(request.sites),
        )

        metadata = {}
        if request.batch_group_id:
            metadata["batch_group_id"] = request.batch_group_id
        if request.chat_id:
            metadata["chat_id"] = request.chat_id
        if request.command_route:
            metadata["command_route"] = request.command_route

        # Create DB record
        async with async_session() as session:
            db_job = ScrapeJob(
                id=job_id,
                status=JobStatus.PENDING.value,
                sites=[site.value for site in request.sites],
                total_items=len(request.items),
                callback_url=request.callback_url,
                priority=request.priority,
                metadata_=metadata or None,
            )
            session.add(db_job)
            await session.commit()

        if settings.job_execution_backend == "celery":
            await self._enqueue_celery_job(job_id, request)
        else:
            # Initialize cache and completion event for local/dev execution.
            self._jobs_cache[job_id] = ScrapeJobResult(
                job_id=job_id,
                status=JobStatus.PENDING,
                total_items=len(request.items),
            )
            self._job_events[job_id] = asyncio.Event()

            # Launch job in background and keep a reference until completion.
            task = asyncio.create_task(self._execute_job(job_id, request))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        return ScrapeJobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            total_items=len(request.items),
            sites=request.sites,
            estimated_duration_seconds=estimated_duration,
        )

    async def _enqueue_celery_job(self, job_id: str, request: ScrapeJobRequest) -> None:
        """Push an existing DB job to the Celery queue."""
        from src.models.database import ScrapeJob, async_session
        from src.tasks.scrape_jobs import execute_scrape_job

        try:
            execute_scrape_job.delay(job_id, request.model_dump(mode="json"))
            logger.info("Job queued in Celery", job_id=job_id)
        except Exception as e:
            logger.error("Failed to queue job in Celery", job_id=job_id, error=str(e))
            async with async_session() as session:
                result = await session.execute(
                    select(ScrapeJob).where(ScrapeJob.id == job_id)
                )
                db_job = result.scalar_one()
                db_job.status = JobStatus.FAILED.value
                db_job.errors = [f"Failed to enqueue Celery task: {e}"]
                db_job.completed_at = datetime.now(UTC)
                await session.commit()
            raise

    async def get_job_status(self, job_id: str) -> ScrapeJobResult | None:
        """Get current status and results for a job."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from src.models.database import ScrapeJob, async_session

        # In local execution, the in-memory job object is updated by the
        # background task and must not be replaced by a stale DB snapshot while
        # the job is running. Celery workers run in another process, so their
        # non-terminal entries still need DB refreshes.
        cached = self._jobs_cache.get(job_id)
        if cached and settings.job_execution_backend == "local":
            return cached
        if cached and cached.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.PARTIAL):
            return cached

        # Fetch from database with eager loading
        async with async_session() as session:
            from src.models.database import ScrapeItem
            
            stmt = (
                select(ScrapeJob)
                .where(ScrapeJob.id == job_id)
                .options(
                    selectinload(ScrapeJob.items).selectinload(ScrapeItem.results)
                )
            )
            result = await session.execute(stmt)
            db_job = result.scalar_one_or_none()

            if not db_job:
                return None

            # Convert ORM to Pydantic
            job_result = await self._orm_to_pydantic(db_job)
            # Update cache
            if settings.job_execution_backend == "local":
                self._jobs_cache[job_id] = job_result
            return job_result

    async def wait_for_job(self, job_id: str, timeout: float = 120.0) -> ScrapeJobResult | None:
        """Wait for a job to complete, using async event instead of polling.
        
        Args:
            job_id: The job ID to wait for
            timeout: Maximum seconds to wait (default 120)
            
        Returns:
            Job result when complete, or None if timeout
        """
        event = self._job_events.get(job_id)
        if not event:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                result = await self.get_job_status(job_id)
                if not result:
                    return None
                if result.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.PARTIAL):
                    return result
                await asyncio.sleep(0.5)
            return None
        
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return await self.get_job_status(job_id)
        except TimeoutError:
            return None


    async def execute_queued_job(self, job_id: str, request: ScrapeJobRequest) -> None:
        """Execute an already-created job from an external worker process."""
        await self._execute_job(job_id, request)

    async def _execute_job(self, job_id: str, request: ScrapeJobRequest) -> None:
        """Execute a scraping job — searches all SKUs across all sites."""
        from src.models.database import PartResultRecord, ScrapeItem, ScrapeJob, async_session

        # A Celery worker runs in a separate process and will not have the API's
        # in-memory cache. Build a local result object so callbacks still include
        # the full job payload.
        job = self._jobs_cache.get(job_id)
        if not job:
            job = ScrapeJobResult(
                job_id=job_id,
                status=JobStatus.PENDING,
                total_items=len(request.items),
            )
            if settings.job_execution_backend == "local":
                self._jobs_cache[job_id] = job

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(UTC)

        start_time = time.monotonic()

        # Update DB status to running
        async with async_session() as session:
            result = await session.execute(
                select(ScrapeJob).where(ScrapeJob.id == job_id)
            )
            db_job = result.scalar_one()
            db_job.status = JobStatus.RUNNING.value
            db_job.started_at = datetime.now(UTC)
            await session.commit()

        try:
            # Process each SKU
            for i, item in enumerate(request.items):
                # Variable delay between searches to avoid rate-limiting
                if i > 0 and settings.scrape_delay_max > 0:
                    delay = random.uniform(settings.scrape_delay_min, settings.scrape_delay_max)
                    logger.debug("Throttle delay", delay_s=round(delay, 2), job_id=job_id)
                    await asyncio.sleep(delay)

                sku_result = await self._search_sku_all_sites(
                    item,
                    request.sites,
                    force_refresh=request.force_refresh,
                )

                # Persist SKU item and results to DB
                async with async_session() as session:
                    db_item = ScrapeItem(
                        job_id=job_id,
                        sku=item.sku,
                        brand=item.brand,
                        description=item.description,
                        status="completed" if sku_result.total_results > 0 else "not_found",
                        site_results=[
                            {
                                "site": site_res.site.value,
                                "site_name": site_res.site_name,
                                "status": site_res.status,
                                "error_message": site_res.error_message,
                                "search_time_ms": site_res.search_time_ms,
                                "from_cache": site_res.from_cache,
                                "cached_at": (
                                    site_res.cached_at.isoformat()
                                    if site_res.cached_at
                                    else None
                                ),
                            }
                            for site_res in sku_result.site_results
                        ],
                    )
                    session.add(db_item)
                    await session.flush()  # Get db_item.id

                    # Insert part results
                    for site_res in sku_result.site_results:
                        for part in site_res.results:
                            db_part = PartResultRecord(
                                item_id=db_item.id,
                                sku_searched=part.sku_searched,
                                sku_found=part.sku_found,
                                exact_match=part.exact_match,
                                site=part.site.value,
                                site_name=part.site_name,
                                price=part.price,
                                currency=part.currency.value,
                                condition=part.condition.value,
                                availability=part.availability,
                                seller_name=part.seller_name,
                                seller_uf=part.seller_uf,
                                seller_company_name=part.seller_company_name,
                                seller_cnpj=part.seller_cnpj,
                                product_url=part.product_url,
                                origin=part.origin,
                                raw_title=part.raw_title,
                                scraped_at=part.scraped_at,
                            )
                            session.add(db_part)
                    await session.commit()

                # Update local result object for local reads and callbacks.
                job.results.append(sku_result)
                job.items_processed = i + 1
                if sku_result.total_results > 0:
                    job.items_succeeded += 1
                else:
                    job.items_failed += 1
                if job.total_items > 0:
                    job.progress_pct = round(job.items_processed / job.total_items * 100, 1)

                # Persist incremental progress counters to the DB so that
                # GET /jobs/{id} returns live numbers while the job runs.
                async with async_session() as session:
                    result = await session.execute(
                        select(ScrapeJob).where(ScrapeJob.id == job_id)
                    )
                    db_job = result.scalar_one()
                    db_job.items_processed = i + 1
                    db_job.items_succeeded = job.items_succeeded
                    db_job.items_failed = job.items_failed
                    await session.commit()

            # Determine final status and persist to DB
            async with async_session() as session:
                result = await session.execute(
                    select(ScrapeJob).where(ScrapeJob.id == job_id)
                )
                db_job = result.scalar_one()

                items_succeeded = job.items_succeeded
                items_failed = job.items_failed
                total_items = db_job.total_items

                if items_succeeded == total_items:
                    final_status = JobStatus.COMPLETED
                elif items_succeeded > 0:
                    final_status = JobStatus.PARTIAL
                else:
                    final_status = JobStatus.FAILED

                db_job.status = final_status.value
                db_job.items_succeeded = items_succeeded
                db_job.items_failed = items_failed
                db_job.items_processed = total_items
                db_job.completed_at = datetime.now(UTC)
                db_job.duration_seconds = time.monotonic() - start_time
                await session.commit()

                job.status = final_status
                job.completed_at = db_job.completed_at
                job.duration_seconds = db_job.duration_seconds
                job.items_processed = total_items
                if job.total_items > 0:
                    job.progress_pct = 100.0
                job.estimated_seconds_remaining = 0
                self._apply_summary_metrics(job)

        except Exception as e:
            logger.error("Job execution failed", job_id=job_id, error=str(e))

            async with async_session() as session:
                result = await session.execute(
                    select(ScrapeJob).where(ScrapeJob.id == job_id)
                )
                db_job = result.scalar_one()
                db_job.status = JobStatus.FAILED.value
                db_job.errors = [str(e)]
                db_job.completed_at = datetime.now(UTC)
                db_job.duration_seconds = time.monotonic() - start_time
                await session.commit()

            job.status = JobStatus.FAILED
            job.errors.append(str(e))
            job.completed_at = datetime.now(UTC)
            job.duration_seconds = time.monotonic() - start_time
            self._apply_summary_metrics(job)

        finally:
            # Signal job completion
            if job_id in self._job_events:
                self._job_events[job_id].set()

            # Send callback if configured
            if request.callback_url:
                await self._send_callback(request.callback_url, job)

            logger.info(
                "Job completed",
                job_id=job_id,
                status=job.status.value,
                succeeded=job.items_succeeded,
                failed=job.items_failed,
                duration=f"{job.duration_seconds:.1f}s",
            )


    async def _scrape_one_site(self, site_id: SiteId, item: SKUItem) -> SiteResult:
        """Run a live scraper for one site."""
        try:
            scraper = await get_scraper(site_id)
            return await scraper.scrape_sku(item.sku, item.brand)
        except NotImplementedError:
            return SiteResult(
                site=site_id,
                site_name=site_id.value,
                status="error",
                error_message=f"Scraper for {site_id.value} not yet implemented",
            )
        except Exception as e:
            return SiteResult(
                site=site_id,
                site_name=site_id.value,
                status="error",
                error_message=str(e),
            )

    async def lookup_sku(
        self,
        sku: str,
        brand: str,
        sites: list[SiteId],
        *,
        force_refresh: bool = False,
    ) -> SKUResult:
        """Synchronous single-SKU lookup for POST /lookup (cache-aware, no Celery)."""
        return await self._search_sku_all_sites(
            SKUItem(sku=sku, brand=brand),
            sites,
            force_refresh=force_refresh,
        )

    async def _search_sku_all_sites(
        self,
        item: SKUItem,
        sites: list[SiteId],
        *,
        force_refresh: bool = False,
    ) -> SKUResult:
        """Resolve each site from cache when possible; scrape only cache misses."""
        from src.services.scrape_cache import scrape_cache

        site_results_by_id: dict[SiteId, SiteResult] = {}
        sites_to_scrape: list[SiteId] = []
        cache_hits = 0

        for site_id in sites:
            if not force_refresh:
                cached = await scrape_cache.get_site_result(item.sku, item.brand, site_id)
                if cached is not None:
                    cached.search_time_ms = 0
                    site_results_by_id[site_id] = cached
                    cache_hits += 1
                    continue
            sites_to_scrape.append(site_id)

        live_scrapes = 0
        if sites_to_scrape:
            if settings.scrape_sites_sequential:
                for site_id in sites_to_scrape:
                    site_result = await self._scrape_one_site(site_id, item)
                    site_results_by_id[site_id] = site_result
                    live_scrapes += 1
                    await scrape_cache.set_site_result(item.sku, item.brand, site_result)
            else:
                semaphore = asyncio.Semaphore(settings.max_concurrent_scrapers)

                async def _search_with_limit(site_id: SiteId) -> tuple[SiteId, SiteResult]:
                    async with semaphore:
                        return site_id, await self._scrape_one_site(site_id, item)

                scraped = await asyncio.gather(
                    *[_search_with_limit(site_id) for site_id in sites_to_scrape]
                )
                for site_id, site_result in scraped:
                    site_results_by_id[site_id] = site_result
                    live_scrapes += 1
                    await scrape_cache.set_site_result(item.sku, item.brand, site_result)

        site_results = [site_results_by_id[site_id] for site_id in sites if site_id in site_results_by_id]
        all_parts = []
        for site_result in site_results:
            all_parts.extend(site_result.results)

        return SKUResult(
            sku=item.sku,
            brand=item.brand,
            site_results=site_results,
            best_price=_find_best_price(all_parts),
            total_results=len(all_parts),
            cache_hits=cache_hits,
            live_scrapes=live_scrapes,
        )

    async def _orm_to_pydantic(self, db_job) -> ScrapeJobResult:
        """Convert SQLAlchemy ORM job to Pydantic model."""
        from src.models.schemas import (
            Currency,
            ItemCondition,
            PartResult,
            SiteId,
            SiteResult,
            SKUResult,
        )

        # Convert all items and results
        sku_results = []
        for db_item in db_job.items:
            # Convert part results for this item
            part_results = [
                PartResult(
                    sku_searched=db_part.sku_searched,
                    sku_found=db_part.sku_found,
                    exact_match=db_part.exact_match,
                    site=SiteId(db_part.site),
                    site_name=db_part.site_name,
                    price=db_part.price,
                    currency=Currency(db_part.currency),
                    condition=ItemCondition(db_part.condition),
                    availability=db_part.availability,
                    seller_name=db_part.seller_name,
                    seller_uf=db_part.seller_uf or "",
                    seller_company_name=db_part.seller_company_name or "",
                    seller_cnpj=db_part.seller_cnpj or "",
                    product_url=db_part.product_url,
                    origin=db_part.origin,
                    scraped_at=db_part.scraped_at,
                    raw_title=db_part.raw_title,
                )
                for db_part in db_item.results
            ]

            # Group by site, then overlay the persisted per-site status snapshot.
            site_map: dict[SiteId, list[PartResult]] = {}
            for part in part_results:
                if part.site not in site_map:
                    site_map[part.site] = []
                site_map[part.site].append(part)

            site_snapshots = db_item.site_results or []
            cache_hits = 0
            if site_snapshots:
                site_results = []
                for snapshot in site_snapshots:
                    cached_at_raw = snapshot.get("cached_at")
                    from_cache = bool(snapshot.get("from_cache"))
                    if from_cache:
                        cache_hits += 1
                    site_results.append(
                        SiteResult(
                            site=SiteId(snapshot["site"]),
                            site_name=snapshot.get("site_name") or snapshot["site"],
                            status=snapshot.get("status", "not_found"),
                            error_message=snapshot.get("error_message", ""),
                            results=site_map.get(SiteId(snapshot["site"]), []),
                            search_time_ms=snapshot.get("search_time_ms", 0),
                            from_cache=from_cache,
                            cached_at=(
                                datetime.fromisoformat(cached_at_raw)
                                if cached_at_raw
                                else None
                            ),
                        )
                    )
            else:
                site_results = [
                    SiteResult(
                        site=site_id,
                        site_name=site_id.value,
                        status="success" if results else "not_found",
                        results=results,
                    )
                    for site_id, results in site_map.items()
                ]

            best_price = _find_best_price(part_results)

            live_scrapes = sum(
                1 for site_result in site_results if not site_result.from_cache
            )
            sku_results.append(
                SKUResult(
                    sku=db_item.sku,
                    brand=db_item.brand,
                    site_results=site_results,
                    best_price=best_price,
                    total_results=len(part_results),
                    cache_hits=cache_hits if site_snapshots else 0,
                    live_scrapes=live_scrapes if site_snapshots else 0,
                )
            )

        job_result = ScrapeJobResult(
            job_id=db_job.id,
            status=JobStatus(db_job.status),
            results=sku_results,
            started_at=db_job.started_at,
            completed_at=db_job.completed_at,
            duration_seconds=db_job.duration_seconds,
            total_items=db_job.total_items,
            items_succeeded=db_job.items_succeeded,
            items_failed=db_job.items_failed,
            items_processed=db_job.items_processed or 0,
            errors=db_job.errors or [],
        )

        if db_job.total_items and db_job.total_items > 0:
            job_result.progress_pct = round(
                job_result.items_processed / db_job.total_items * 100, 1
            )
        if job_result.items_processed > 0 and db_job.started_at:
            started = db_job.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=UTC)
            elapsed = (datetime.now(UTC) - started).total_seconds()
            remaining_items = db_job.total_items - job_result.items_processed
            if remaining_items > 0 and elapsed > 0:
                job_result.estimated_seconds_remaining = int(
                    elapsed / job_result.items_processed * remaining_items
                )

        self._apply_summary_metrics(job_result)
        return job_result


    async def _send_callback(self, url: str, job: ScrapeJobResult) -> None:
        """Send job results to an external callback URL."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json=job.model_dump(mode="json"),
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Secret": settings.callback_webhook_secret,
                    },
                )
                logger.info(
                    "Callback sent",
                    url=url,
                    status_code=response.status_code,
                    job_id=job.job_id,
                )
        except Exception as e:
            logger.error("Callback failed", url=url, error=str(e))


# Singleton instance
orchestrator = Orchestrator()
