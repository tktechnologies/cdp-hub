from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import IngestionError


class ErrorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_error(
        self,
        *,
        correlation_id: str,
        error_code: str,
        error_type: str,
        message: str,
        job_id: UUID | None = None,
        job_item_id: UUID | None = None,
        sku: str | None = None,
        retryable: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> IngestionError:
        row = IngestionError(
            correlation_id=correlation_id,
            job_id=job_id,
            job_item_id=job_item_id,
            sku=sku,
            error_code=error_code,
            error_type=error_type,
            message=message,
            retryable=retryable,
            metadata_json=metadata or {},
        )
        self._session.add(row)
        await self._session.flush()
        return row
