"""SkuProcessor duplicate/cache behavior.

Verifies the N-in → N-out contract: duplicate SKUs in one job reuse the first
result (no second upstream call), cross-job Redis cache hits skip the upstream
call, and live fetches populate the cache.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.sku_cache import CachedSku
from app.workers.sku_processor import SkuProcessor


def _make_item(sku: str) -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), sku=sku)


@pytest.fixture
def deps():
    auth = AsyncMock()
    client = AsyncMock()
    snapshot_repo = AsyncMock()
    snapshot_repo.save_snapshot = AsyncMock(return_value=SimpleNamespace(id=uuid4()))
    api_data_repo = AsyncMock()
    error_repo = AsyncMock()
    return auth, client, snapshot_repo, api_data_repo, error_repo


def _build(deps, sku_cache=None) -> SkuProcessor:
    auth, client, snapshot_repo, api_data_repo, error_repo = deps
    return SkuProcessor(
        auth_service=auth,
        muvstok_client=client,
        snapshot_repository=snapshot_repo,
        api_data_repository=api_data_repo,
        error_repository=error_repo,
        sku_cache=sku_cache,
    )


async def test_duplicate_sku_reused_from_in_job_memo(deps):
    _, client, _, api_data_repo, _ = deps
    client.fetch_sku = AsyncMock(return_value=([{"sku": "ABC", "price": 10}], 200))
    processor = _build(deps, sku_cache=None)
    job_id = uuid4()

    r1, _ = await processor.process_item(
        job_id=job_id, correlation_id="c", item=_make_item("ABC"), token="t"
    )
    r2, _ = await processor.process_item(
        job_id=job_id, correlation_id="c", item=_make_item("ABC"), token="t"
    )

    assert client.fetch_sku.await_count == 1  # duplicate not re-requested upstream
    assert r1.status == "succeeded" and r2.status == "succeeded"
    assert r1.rows == r2.rows == [{"sku": "ABC", "price": 10}]
    assert r1.from_cache is False and r2.from_cache is True
    assert api_data_repo.save_result.await_count == 2  # both rows persisted (N results)


async def test_duplicate_sku_reused_even_with_separator_variants(deps):
    _, client, _, _, _ = deps
    client.fetch_sku = AsyncMock(return_value=([{"x": 1}], 200))
    processor = _build(deps, sku_cache=None)
    job_id = uuid4()

    await processor.process_item(job_id=job_id, correlation_id="c", item=_make_item("AB-12"), token="t")
    r2, _ = await processor.process_item(
        job_id=job_id, correlation_id="c", item=_make_item("ab12"), token="t"
    )

    assert client.fetch_sku.await_count == 1
    assert r2.from_cache is True


async def test_not_found_duplicate_reused(deps):
    _, client, _, _, _ = deps
    client.fetch_sku = AsyncMock(return_value=([], 404))
    processor = _build(deps, sku_cache=None)
    job_id = uuid4()

    r1, _ = await processor.process_item(
        job_id=job_id, correlation_id="c", item=_make_item("NF"), token="t"
    )
    r2, _ = await processor.process_item(
        job_id=job_id, correlation_id="c", item=_make_item("NF"), token="t"
    )

    assert client.fetch_sku.await_count == 1
    assert r1.status == "failed" and r1.error_code == "not_found"
    assert r2.status == "failed" and r2.error_code == "not_found" and r2.from_cache is True


async def test_redis_cache_hit_skips_upstream(deps):
    _, client, _, _, _ = deps
    client.fetch_sku = AsyncMock()
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=CachedSku(status="succeeded", rows=[{"a": 1}]))
    processor = _build(deps, sku_cache=cache)

    result, _ = await processor.process_item(
        job_id=uuid4(), correlation_id="c", item=_make_item("ZZ"), token="t"
    )

    client.fetch_sku.assert_not_called()
    assert result.status == "succeeded" and result.rows == [{"a": 1}] and result.from_cache is True


async def test_live_fetch_populates_cache(deps):
    _, client, _, _, _ = deps
    client.fetch_sku = AsyncMock(return_value=([{"a": 1}], 200))
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    processor = _build(deps, sku_cache=cache)

    await processor.process_item(
        job_id=uuid4(), correlation_id="c", item=_make_item("FRESH"), token="t"
    )

    cache.set.assert_awaited_once()
    args = cache.set.await_args.args
    assert args[0] == "FRESH" and args[1] == "succeeded" and args[2] == [{"a": 1}]
