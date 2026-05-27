from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CallbackAttempt
from app.domain.job_status import CallbackStatus


class CallbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_attempt(
        self,
        *,
        job_id: UUID,
        correlation_id: str,
        status: CallbackStatus,
        attempt: int,
        callback_url: str,
        response_status_code: int | None = None,
        error_code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CallbackAttempt:
        row = CallbackAttempt(
            job_id=job_id,
            correlation_id=correlation_id,
            status=status,
            attempt=attempt,
            callback_url=callback_url,
            response_status_code=response_status_code,
            error_code=error_code,
            metadata_json=metadata or {},
        )
        self._session.add(row)
        await self._session.flush()
        return row
