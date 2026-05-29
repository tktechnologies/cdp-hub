"""Per-SKU Muvstok result cache (Redis).

Holds the rows returned for a SKU so repeated lookups — duplicate SKUs within a job
and the same SKU across jobs within the TTL window — reuse the stored result instead
of hitting the upstream Muvstok API again. Mirrors the scraper's 24h scrape cache.

Only cacheable outcomes are stored: ``succeeded`` (rows) and ``not_found`` (empty).
Transient failures (HTTP/timeout) are never cached so they get retried next time.
All Redis access is best-effort: any error degrades to a cache miss/no-op.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis

from app.core.config import Settings

logger = logging.getLogger("muvstok.sku_cache")

SKU_CACHE_PREFIX = "muvstok:sku:v1:"
CACHEABLE_STATUSES = ("succeeded", "not_found")


def normalize_cache_sku(sku: str) -> str:
    """Stable cache key fragment (strip separators, upper-case)."""
    return re.sub(r"[\s\-\./]", "", str(sku or "").strip()).upper()


def build_cache_key(sku: str) -> str:
    return f"{SKU_CACHE_PREFIX}{normalize_cache_sku(sku)}"


@dataclass(slots=True)
class CachedSku:
    status: str
    rows: list[dict[str, Any]]


class SkuCache:
    """Thin async Redis wrapper for per-SKU Muvstok results."""

    def __init__(self, settings: Settings, redis: Redis | None = None) -> None:
        self._settings = settings
        self._enabled = settings.muvstok_cache_enabled
        self._redis = redis
        if self._enabled and self._redis is None:
            self._redis = Redis.from_url(settings.sku_cache_redis_url, decode_responses=True)

    @property
    def enabled(self) -> bool:
        return self._enabled and self._redis is not None

    def _ttl_for_status(self, status: str) -> int | None:
        if status == "succeeded":
            return self._settings.muvstok_cache_ttl_seconds
        if status == "not_found":
            return self._settings.muvstok_cache_ttl_not_found_seconds
        return None

    async def get(self, sku: str) -> CachedSku | None:
        if not self.enabled:
            return None
        key = build_cache_key(sku)
        try:
            raw = await self._redis.get(key)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001 — cache is best-effort
            logger.warning("sku_cache_get_failed", extra={"sku": sku, "error": str(exc)})
            return None
        if not raw:
            return None
        try:
            payload = json.loads(raw)
            return CachedSku(status=str(payload["status"]), rows=list(payload.get("rows") or []))
        except (ValueError, KeyError, TypeError):
            return None

    async def set(self, sku: str, status: str, rows: list[dict[str, Any]]) -> None:
        if not self.enabled or status not in CACHEABLE_STATUSES:
            return
        ttl = self._ttl_for_status(status)
        if ttl is None:
            return
        key = build_cache_key(sku)
        payload = json.dumps({"status": status, "rows": rows})
        try:
            await self._redis.setex(key, ttl, payload)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001 — cache is best-effort
            logger.warning("sku_cache_set_failed", extra={"sku": sku, "error": str(exc)})

    async def close(self) -> None:
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception as exc:  # noqa: BLE001 — best-effort close
                logger.debug("sku_cache_close_failed", extra={"error": str(exc)})
