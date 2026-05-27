from dataclasses import dataclass
from uuid import UUID

from app.domain.job_status import JobStatus


@dataclass(frozen=True)
class JobSummary:
    id: UUID
    correlation_id: str
    status: JobStatus
    submitted_sku_count: int
    succeeded_sku_count: int
    failed_sku_count: int
