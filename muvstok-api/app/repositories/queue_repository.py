from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import QueueMessage
from app.domain.job_status import QueueMessageStatus


class QueueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_published(
        self,
        job_id: UUID,
        correlation_id: str,
        queue_name: str,
        redis_message_id: str,
        payload: dict[str, Any],
    ) -> QueueMessage:
        message = QueueMessage(
            job_id=job_id,
            correlation_id=correlation_id,
            queue_name=queue_name,
            redis_message_id=redis_message_id,
            status=QueueMessageStatus.PUBLISHED,
            payload=payload,
        )
        self._session.add(message)
        await self._session.commit()
        await self._session.refresh(message)
        return message
