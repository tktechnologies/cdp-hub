"""Redis-backed scrape result cache with optional PostgreSQL warm fallback."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import structlog
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.config import settings
from src.models.schemas import (
    Currency,
    ItemCondition,
    PartResult,
    SiteId,
    SiteResult,
)
from src.redis_keys import SCRAPE_CACHE_PREFIX
from src.utils.monitoring import scrape_cache_hit_total, scrape_cache_miss_total

logger = structlog.get_logger()


def normalize_cache_sku(sku: str, brand: str = "", site_id: SiteId | None = None) -> str:
    """Match BaseScraper SKU normalization for stable cache keys."""
    normalized = re.sub(r"[\s\-\.\/]", "", sku.strip()).upper()
    if (
        brand.lower() in ("mercedes", "mb", "mercedes-benz")
        and site_id == SiteId.EUROPE
        and len(normalized) > 1
    ):
        normalized = normalized[1:]
    return normalized


def build_cache_key(sku: str, brand: str, site_id: SiteId) -> str:
    """Build a Redis key for one site + SKU + brand."""
    sku_key = normalize_cache_sku(sku, brand, site_id)
    brand_key = re.sub(r"[^\w]", "", brand.strip().lower()) or "_"
    return f"{SCRAPE_CACHE_PREFIX}{site_id.value}:{brand_key}:{sku_key}"


def normalize_redis_tls_url(url: str) -> tuple[str, dict[str, Any]]:
    """Return a Redis URL/kwargs pair that works across redis-py TLS versions."""
    if not url.startswith("rediss://"):
        return url, {}

    parsed = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() != "ssl_cert_reqs"
    ]
    normalized_url = urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query),
            parsed.fragment,
        )
    )
    return normalized_url, {"ssl_cert_reqs": "none"}


class ScrapeCacheService:
    """Per-site SKU result cache in Redis with PostgreSQL warm fallback."""

    def __init__(self) -> None:
        self._client: Redis | None = None
        self._redis_unavailable = False

    async def _get_redis(self) -> Redis | None:
        if not settings.scrape_cache_enabled or self._redis_unavailable:
            return None
        if self._client is None:
            try:
                redis_kwargs: dict[str, Any] = {"decode_responses": True}
                redis_url, tls_kwargs = normalize_redis_tls_url(settings.scrape_cache_redis_url)
                redis_kwargs.update(tls_kwargs)
                self._client = Redis.from_url(
                    redis_url,
                    **redis_kwargs,
                )
                await self._client.ping()
            except Exception as exc:
                self._redis_unavailable = True
                logger.warning(
                    "Scrape cache Redis unavailable; live scrapes only",
                    error=str(exc),
                )
                return None
        return self._client

    def _ttl_for_status(self, status: str) -> int | None:
        normalized = status.lower()
        bypass = {value.strip().lower() for value in settings.scrape_cache_bypass_statuses}
        if normalized in bypass:
            return None
        if normalized == "not_found":
            return settings.scrape_cache_ttl_not_found_seconds
        if normalized == "blocked":
            return settings.scrape_cache_ttl_blocked_seconds
        if normalized in {"success", "no_price"}:
            return settings.scrape_cache_ttl_seconds
        return None

    @staticmethod
    def _payload_to_site_result(data: dict[str, Any]) -> SiteResult:
        site_result = SiteResult.model_validate(data["site_result"])
        site_result.from_cache = True
        site_result.search_time_ms = 0
        cached_at_raw = data.get("cached_at")
        if cached_at_raw:
            site_result.cached_at = datetime.fromisoformat(cached_at_raw)
        return site_result

    @staticmethod
    def _site_result_payload(
        site_result: SiteResult,
        *,
        sku: str,
        brand: str,
    ) -> dict[str, Any]:
        cached_at = site_result.cached_at or datetime.now(UTC)
        return {
            "sku": sku,
            "brand": brand,
            "cached_at": cached_at.isoformat(),
            "site_result": site_result.model_dump(mode="json"),
        }

    async def get_site_result(
        self,
        sku: str,
        brand: str,
        site_id: SiteId,
    ) -> SiteResult | None:
        """Return a cached site result or None on miss."""
        if not settings.scrape_cache_enabled:
            scrape_cache_miss_total.inc()
            return None

        redis = await self._get_redis()
        key = build_cache_key(sku, brand, site_id)

        if redis is not None:
            try:
                raw = await redis.get(key)
                if raw:
                    data = json.loads(raw)
                    result = self._payload_to_site_result(data)
                    logger.info(
                        "Scrape cache hit",
                        site=site_id.value,
                        sku=sku,
                        source="redis",
                        status=result.status,
                    )
                    scrape_cache_hit_total.labels(source="redis").inc()
                    return result
            except Exception as exc:
                logger.warning(
                    "Scrape cache Redis read failed",
                    site=site_id.value,
                    sku=sku,
                    error=str(exc),
                )

        if settings.scrape_cache_pg_fallback:
            pg_result = await self._get_from_postgres(sku, brand, site_id)
            if pg_result is not None:
                await self.set_site_result(sku, brand, pg_result)
                logger.info(
                    "Scrape cache hit",
                    site=site_id.value,
                    sku=sku,
                    source="postgresql",
                    status=pg_result.status,
                )
                scrape_cache_hit_total.labels(source="postgresql").inc()
                return pg_result

        scrape_cache_miss_total.inc()
        return None

    async def set_site_result(
        self,
        sku: str,
        brand: str,
        site_result: SiteResult,
    ) -> None:
        """Store a live scrape snapshot in Redis when the status is cacheable."""
        if not settings.scrape_cache_enabled:
            return

        ttl = self._ttl_for_status(site_result.status)
        if ttl is None:
            return

        redis = await self._get_redis()
        if redis is None:
            return

        if site_result.cached_at is None:
            site_result.cached_at = datetime.now(UTC)

        key = build_cache_key(sku, brand, site_result.site)
        payload = json.dumps(
            self._site_result_payload(site_result, sku=sku, brand=brand),
            ensure_ascii=False,
        )

        try:
            await redis.setex(key, ttl, payload)
            logger.debug(
                "Scrape cache stored",
                site=site_result.site.value,
                sku=sku,
                status=site_result.status,
                ttl_seconds=ttl,
            )
        except Exception as exc:
            logger.warning(
                "Scrape cache Redis write failed",
                site=site_result.site.value,
                sku=sku,
                error=str(exc),
            )

    async def _get_from_postgres(
        self,
        sku: str,
        brand: str,
        site_id: SiteId,
    ) -> SiteResult | None:
        """Rebuild a site result from the latest persisted job within the TTL window."""
        from src.models.database import ScrapeItem, ScrapeJob, async_session

        cutoff = datetime.now(UTC) - timedelta(seconds=settings.scrape_cache_ttl_seconds)

        async with async_session() as session:
            stmt = (
                select(ScrapeItem)
                .join(ScrapeJob, ScrapeItem.job_id == ScrapeJob.id)
                .where(ScrapeItem.sku == sku)
                .where(ScrapeItem.brand == brand)
                .options(selectinload(ScrapeItem.results))
                .order_by(ScrapeJob.created_at.desc())
                .limit(20)
            )
            result = await session.execute(stmt)
            items = result.scalars().all()

            for item in items:
                snapshot = self._snapshot_for_site(item.site_results or [], site_id)
                if snapshot is None:
                    continue

                parts = [
                    row
                    for row in item.results
                    if row.site == site_id.value
                    and (row.scraped_at is None or row.scraped_at >= cutoff)
                ]
                if not parts and snapshot.get("status") not in {"not_found", "blocked"}:
                    continue

                latest_scraped = max(
                    (row.scraped_at for row in parts if row.scraped_at),
                    default=None,
                )
                if latest_scraped is None and snapshot.get("status") in {
                    "not_found",
                    "blocked",
                    "error",
                    "timeout",
                }:
                    latest_scraped = datetime.now(UTC)

                if latest_scraped and latest_scraped < cutoff:
                    continue

                return self._build_site_result_from_db(
                    site_id=site_id,
                    snapshot=snapshot,
                    parts=parts,
                    cached_at=latest_scraped,
                )

        return None

    @staticmethod
    def _snapshot_for_site(
        snapshots: list[dict[str, Any]],
        site_id: SiteId,
    ) -> dict[str, Any] | None:
        for snapshot in snapshots:
            if snapshot.get("site") == site_id.value:
                return snapshot
        return None

    @staticmethod
    def _build_site_result_from_db(
        *,
        site_id: SiteId,
        snapshot: dict[str, Any],
        parts: list[Any],
        cached_at: datetime | None,
    ) -> SiteResult:
        part_results = [
            PartResult(
                sku_searched=row.sku_searched,
                sku_found=row.sku_found,
                exact_match=row.exact_match,
                site=SiteId(row.site),
                site_name=row.site_name,
                price=row.price,
                currency=Currency(row.currency),
                condition=ItemCondition(row.condition),
                availability=row.availability,
                seller_name=row.seller_name,
                seller_uf=row.seller_uf or "",
                seller_company_name=row.seller_company_name or "",
                seller_cnpj=row.seller_cnpj or "",
                product_url=row.product_url,
                origin=row.origin,
                scraped_at=row.scraped_at or datetime.now(UTC),
                raw_title=row.raw_title,
            )
            for row in parts
        ]
        return SiteResult(
            site=site_id,
            site_name=snapshot.get("site_name") or site_id.value,
            status=snapshot.get("status", "not_found"),
            error_message=snapshot.get("error_message", ""),
            results=part_results,
            search_time_ms=snapshot.get("search_time_ms", 0),
            from_cache=True,
            cached_at=cached_at,
        )


scrape_cache = ScrapeCacheService()
