"""Unit tests for QueueService."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.queue_service import QueueService


@pytest.mark.asyncio
async def test_publish_job_writes_redis_and_records_repository() -> None:
    job_id = uuid4()
    correlation_id = "corr-queue-1"
    sku_count = 3
    redis_message_id = "1700000000001-0"

    queue_client = AsyncMock()
    queue_client.publish_job = AsyncMock(return_value=redis_message_id)
    queue_client.job_stream_name = "muvstok:jobs"

    queue_repository = AsyncMock()
    service = QueueService(queue_client, queue_repository)

    result = await service.publish_job(job_id, correlation_id, sku_count)

    assert result == redis_message_id
    expected_payload = {
        "job_id": str(job_id),
        "correlation_id": correlation_id,
        "sku_count": sku_count,
    }
    queue_client.publish_job.assert_awaited_once_with(expected_payload)
    queue_repository.record_published.assert_awaited_once_with(
        job_id=job_id,
        correlation_id=correlation_id,
        queue_name="muvstok:jobs",
        redis_message_id=redis_message_id,
        payload=expected_payload,
    )


@pytest.mark.asyncio
async def test_close_closes_queue_client() -> None:
    queue_client = AsyncMock()
    queue_repository = AsyncMock()
    service = QueueService(queue_client, queue_repository)

    await service.close()

    queue_client.close.assert_awaited_once()
