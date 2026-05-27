from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MuvstokRawSnapshot


class SnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_snapshot(
        self,
        *,
        job_id: UUID,
        job_item_id: UUID,
        correlation_id: str,
        sku: str,
        raw_response: dict[str, Any],
        request_metadata: dict[str, Any] | None = None,
        response_metadata: dict[str, Any] | None = None,
    ) -> MuvstokRawSnapshot:
        snapshot = MuvstokRawSnapshot(
            job_id=job_id,
            job_item_id=job_item_id,
            correlation_id=correlation_id,
            sku=sku,
            request_metadata=request_metadata or {},
            response_metadata=response_metadata or {},
            raw_response=raw_response,
            governance_metadata={},
        )
        self._session.add(snapshot)
        await self._session.flush()
        return snapshot
