"""SkuCache (Redis) unit tests with a fake redis client."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

from app.core.config import Settings
from app.services.sku_cache import CachedSku, SkuCache, build_cache_key, normalize_cache_sku


def _settings(**kwargs) -> Settings:
    base = dict(environment="test", muvstok_cache_enabled=True)
    base.update(kwargs)
    return Settings(**base)


def test_normalize_and_key():
    assert normalize_cache_sku(" ab-12.3/4 ") == "AB1234"
    assert build_cache_key("ab12") == "muvstok:sku:v1:AB12"


async def test_get_returns_none_on_miss():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    cache = SkuCache(_settings(), redis=redis)
    assert await cache.get("X") is None


async def test_get_parses_payload():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=json.dumps({"status": "succeeded", "rows": [{"a": 1}]}))
    cache = SkuCache(_settings(), redis=redis)
    result = await cache.get("X")
    assert result == CachedSku(status="succeeded", rows=[{"a": 1}])


async def test_set_uses_status_ttl():
    redis = AsyncMock()
    redis.setex = AsyncMock()
    cache = SkuCache(
        _settings(muvstok_cache_ttl_seconds=111, muvstok_cache_ttl_not_found_seconds=22),
        redis=redis,
    )
    await cache.set("X", "FOUND_PRICE", [{"price": 1}])
    await cache.set("Z", "NO_PRICE", [{"sku": "Z"}])
    await cache.set("Y", "not_found", [])
    ttls = [call.args[1] for call in redis.setex.await_args_list]
    assert ttls == [111, 111, 22]


async def test_set_ignores_non_cacheable_status():
    redis = AsyncMock()
    redis.setex = AsyncMock()
    cache = SkuCache(_settings(), redis=redis)
    await cache.set("X", "failed", [])
    redis.setex.assert_not_called()


async def test_disabled_cache_is_noop():
    cache = SkuCache(_settings(muvstok_cache_enabled=False))
    assert cache.enabled is False
    assert await cache.get("X") is None
    await cache.set("X", "succeeded", [{"a": 1}])  # no redis, no error


async def test_get_degrades_to_miss_on_redis_error():
    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=RuntimeError("redis down"))
    cache = SkuCache(_settings(), redis=redis)
    assert await cache.get("X") is None
