from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.domain.job_status import JobItemStatus, JobStatus


class JobAcceptedResponse(BaseModel):
    job_id: UUID
    correlation_id: str
    status: JobStatus
    submitted_sku_count: int
    queued_at: datetime


class JobItemResponse(BaseModel):
    sku: str
    status: JobItemStatus
    attempts: int
    last_error_code: str | None = None


class JobStatusResponse(BaseModel):
    job_id: UUID
    correlation_id: str
    status: JobStatus
    submitted_sku_count: int
    succeeded_sku_count: int
    failed_sku_count: int
    processed_sku_count: int | None = None
    progress_pct: float | None = None
    estimated_seconds_remaining: int | None = None
    callback_status: str | None = None
    items: list[JobItemResponse]
    items_limit: int
    items_offset: int
    items_returned: int
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
