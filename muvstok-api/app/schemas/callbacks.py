from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CallbackJobItem(BaseModel):
    sku: str
    status: str
    snapshot_id: UUID | None = None
    error_code: str | None = None
    sku_result: str = ""
    source_health: str = ""
    has_valid_price: bool = False


class MuvstokCallbackPayload(BaseModel):
    job_id: UUID
    correlation_id: str
    status: str
    submitted_sku_count: int
    succeeded_sku_count: int
    failed_sku_count: int
    found_sku_count: int = 0
    no_price_sku_count: int = 0
    not_found_sku_count: int = 0
    blocked_sku_count: int = 0
    error_sku_count: int = 0
    items: list[CallbackJobItem]
    results: list[dict[str, Any]] = []
    metadata: dict[str, Any]
    started_at: datetime | None = None
    duration_seconds: float | None = None
    completed_at: datetime
