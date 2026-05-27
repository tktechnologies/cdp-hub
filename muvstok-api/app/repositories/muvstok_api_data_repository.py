from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MuvstokApiData


class MuvstokApiDataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_result(
        self,
        *,
        job_id: UUID,
        job_item_id: UUID,
        correlation_id: str,
        sku: str,
        response_status: str,
        muvstok_payload: dict[str, Any],
        request_metadata: dict[str, Any] | None = None,
        response_metadata: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MuvstokApiData:
        existing = await self.get_by_job_item(job_item_id)
        if existing is None:
            existing = MuvstokApiData(
                job_id=job_id,
                job_item_id=job_item_id,
                correlation_id=correlation_id,
                sku=sku,
                response_status=response_status,
                muvstok_payload=muvstok_payload,
                request_metadata=request_metadata or {},
                response_metadata=response_metadata or {},
                metadata_json=metadata or {},
            )
            self._session.add(existing)
        else:
            existing.response_status = response_status
            existing.muvstok_payload = muvstok_payload
            existing.request_metadata = request_metadata or {}
            existing.response_metadata = response_metadata or {}
            existing.metadata_json = metadata or {}

        await self._session.flush()
        await self._session.refresh(existing)
        return existing

    async def get_by_job_item(self, job_item_id: UUID) -> MuvstokApiData | None:
        result = await self._session.execute(
            select(MuvstokApiData).where(MuvstokApiData.job_item_id == job_item_id)
        )
        return result.scalar_one_or_none()

    async def list_by_job(
        self,
        job_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MuvstokApiData]:
        result = await self._session.execute(
            select(MuvstokApiData)
            .where(MuvstokApiData.job_id == job_id)
            .order_by(MuvstokApiData.created_at, MuvstokApiData.sku)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
