"""Unit tests for JobService."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.exceptions import JobLimitExceededError
from app.domain.job_status import JobStatus
from app.schemas.requests import CreateMuvstokJobRequest
from app.services.job_service import JobService
from tests.conftest import make_job


@pytest.mark.asyncio
async def test_create_job_rejects_sku_limit(
    settings,
    api_client,
    mock_job_repository,
    mock_queue_service,
) -> None:
    settings.max_skus_per_job = 1
    service = JobService(settings, mock_job_repository, mock_queue_service)
    request = CreateMuvstokJobRequest(
        skus=["A", "B"],
        callback_url="https://example.com/webhook/muvstok-result",
    )

    with pytest.raises(JobLimitExceededError):
        await service.create_job(request, api_client)

    mock_job_repository.create_job.assert_not_called()
    mock_queue_service.publish_job.assert_not_called()


@pytest.mark.asyncio
async def test_create_job_returns_existing_on_idempotency_hit(
    settings,
    api_client,
    sample_request,
    mock_job_repository,
    mock_queue_service,
) -> None:
    existing = make_job(status=JobStatus.QUEUED)
    mock_job_repository.get_by_idempotency_key = AsyncMock(return_value=existing)

    service = JobService(settings, mock_job_repository, mock_queue_service)
    response = await service.create_job(sample_request, api_client)

    assert response.job_id == existing.id
    assert response.correlation_id == existing.correlation_id
    assert response.status == JobStatus.QUEUED
    mock_job_repository.create_job.assert_not_called()
    mock_queue_service.publish_job.assert_not_called()


@pytest.mark.asyncio
async def test_create_job_publishes_and_marks_queued(
    settings,
    api_client,
    sample_request,
    mock_job_repository,
    mock_queue_service,
) -> None:
    pending = make_job(status=JobStatus.PENDING)
    queued = make_job(job_id=pending.id, status=JobStatus.QUEUED)

    mock_job_repository.get_by_idempotency_key = AsyncMock(return_value=None)
    mock_job_repository.create_job = AsyncMock(return_value=pending)
    mock_job_repository.mark_queued = AsyncMock(return_value=queued)

    service = JobService(settings, mock_job_repository, mock_queue_service)
    response = await service.create_job(sample_request, api_client)

    mock_queue_service.publish_job.assert_awaited_once_with(
        job_id=pending.id,
        correlation_id=pending.correlation_id,
        sku_count=pending.submitted_sku_count,
    )
    mock_job_repository.mark_queued.assert_awaited_once_with(pending.id)
    assert response.job_id == queued.id
    assert response.status == JobStatus.QUEUED


@pytest.mark.asyncio
async def test_create_job_requires_queue_service(
    settings,
    api_client,
    sample_request,
    mock_job_repository,
) -> None:
    pending = make_job(status=JobStatus.PENDING)
    mock_job_repository.get_by_idempotency_key = AsyncMock(return_value=None)
    mock_job_repository.create_job = AsyncMock(return_value=pending)

    service = JobService(settings, mock_job_repository, queue_service=None)

    with pytest.raises(RuntimeError, match="Queue service is required"):
        await service.create_job(sample_request, api_client)


@pytest.mark.asyncio
async def test_get_job_delegates_to_repository(
    settings,
    mock_job_repository,
    mock_queue_service,
) -> None:
    job_id = uuid4()
    expected = object()
    mock_job_repository.get_job_status = AsyncMock(return_value=expected)

    service = JobService(settings, mock_job_repository, mock_queue_service)
    result = await service.get_job(job_id, items_limit=50, items_offset=0)

    mock_job_repository.get_job_status.assert_awaited_once_with(job_id, 50, 0)
    assert result is expected


@pytest.mark.asyncio
async def test_close_closes_queue_service(
    settings,
    mock_job_repository,
    mock_queue_service,
) -> None:
    service = JobService(settings, mock_job_repository, mock_queue_service)
    await service.close()
    mock_queue_service.close.assert_awaited_once()
