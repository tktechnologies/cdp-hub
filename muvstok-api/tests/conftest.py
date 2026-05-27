"""Shared fixtures for StokAPI unit and contract tests."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.api.dependencies import ApiClientContext
from app.core.config import Settings
from app.domain.job_status import JobStatus
from app.schemas.requests import CreateMuvstokJobRequest


@pytest.fixture
def settings() -> Settings:
    return Settings(
        max_skus_per_job=100,
        job_item_batch_size=10,
        environment="test",
    )


@pytest.fixture
def api_client() -> ApiClientContext:
    return ApiClientContext(client_id="test-client")


@pytest.fixture
def sample_request() -> CreateMuvstokJobRequest:
    return CreateMuvstokJobRequest(
        skus=["SKU1", "SKU2"],
        callback_url="https://example.com/webhook/muvstok-result",
        metadata={"chat_id": "123"},
        idempotency_key="idem-1",
    )


@pytest.fixture
def mock_job_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_queue_service() -> AsyncMock:
    service = AsyncMock()
    service.publish_job = AsyncMock(return_value="1700000000000-0")
    return service


def make_job(
    *,
    job_id: UUID | None = None,
    correlation_id: str = "corr-test",
    status: JobStatus = JobStatus.PENDING,
    submitted_sku_count: int = 2,
    idempotency_key: str | None = "idem-1",
) -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=job_id or uuid4(),
        correlation_id=correlation_id,
        status=status,
        submitted_sku_count=submitted_sku_count,
        updated_at=now,
        idempotency_key=idempotency_key,
    )
