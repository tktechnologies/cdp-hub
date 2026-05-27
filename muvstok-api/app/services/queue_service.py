import logging
from typing import Any
from uuid import UUID

from app.clients.redis_queue_client import RedisQueueClient
from app.repositories.queue_repository import QueueRepository

logger = logging.getLogger("muvstok.queue")


class QueueService:
    def __init__(self, queue_client: RedisQueueClient, queue_repository: QueueRepository) -> None:
        self._queue_client = queue_client
        self._queue_repository = queue_repository

    async def publish_job(self, job_id: UUID, correlation_id: str, sku_count: int) -> str:
        payload: dict[str, Any] = {
            "job_id": str(job_id),
            "correlation_id": correlation_id,
            "sku_count": sku_count,
        }
        redis_message_id = await self._queue_client.publish_job(payload)
        await self._queue_repository.record_published(
            job_id=job_id,
            correlation_id=correlation_id,
            queue_name=self._queue_client.job_stream_name,
            redis_message_id=redis_message_id,
            payload=payload,
        )
        logger.info(
            "job_published_to_redis",
            extra={
                "event_name": "job_published_to_redis",
                "service": "muvstok-api",
                "job_id": str(job_id),
                "correlation_id": correlation_id,
                "queue_message_id": redis_message_id,
                "status": "published",
            },
        )
        return redis_message_id

    async def close(self) -> None:
        await self._queue_client.close()
