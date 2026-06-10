import asyncio
import logging
from uuid import UUID

from redis.exceptions import RedisError

from app.clients.redis_queue_client import RedisQueueClient
from app.core.config import get_settings
from app.workers.job_processor import JobProcessor

logger = logging.getLogger("muvstok.worker")


async def run_worker() -> None:
    settings = get_settings()
    queue_client = RedisQueueClient(settings)
    processor = JobProcessor(settings)

    try:
        while True:
            try:
                messages = await queue_client.read_jobs(
                    count=settings.worker_jobs_per_read,
                    block_ms=settings.redis_read_block_ms,
                )
            except (RedisError, TimeoutError, OSError) as exc:
                logger.warning(
                    "redis_read_failed",
                    extra={
                        "event_name": "redis_read_failed",
                        "error_type": type(exc).__name__,
                    },
                )
                await asyncio.sleep(5)
                continue
            if not messages:
                continue
            for message in messages:
                message_id = message["message_id"]
                fields = message["fields"]
                try:
                    await processor.process_job(UUID(fields["job_id"]))
                    await queue_client.acknowledge(message_id)
                except NotImplementedError:
                    logger.exception(
                        "job_processor_not_implemented",
                        extra={
                            "event_name": "job_processor_not_implemented",
                            "job_id": fields.get("job_id"),
                            "correlation_id": fields.get("correlation_id"),
                        },
                    )
                    raise
                except Exception as exc:
                    logger.exception(
                        "job_processing_failed",
                        extra={
                            "event_name": "job_processing_failed",
                            "job_id": fields.get("job_id"),
                            "correlation_id": fields.get("correlation_id"),
                        },
                    )
                    await queue_client.dead_letter(
                        message_id,
                        {
                            "job_id": fields.get("job_id", ""),
                            "correlation_id": fields.get("correlation_id", ""),
                            "error_type": type(exc).__name__,
                        },
                    )
    finally:
        await queue_client.close()


if __name__ == "__main__":
    asyncio.run(run_worker())
