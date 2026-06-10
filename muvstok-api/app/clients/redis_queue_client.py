from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.core.config import Settings

# Redis Streams on DB 0: muvstok:jobs, muvstok:jobs:dead-letter (see docs/DATABASE.md).
RedisField = bytes | bytearray | memoryview | str | int | float


class RedisQueueClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        read_timeout_seconds = max(
            float(settings.redis_socket_timeout_seconds),
            (float(settings.redis_read_block_ms) / 1000.0) + 5.0,
        )
        self._redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=read_timeout_seconds,
            socket_connect_timeout=settings.redis_socket_connect_timeout_seconds,
            health_check_interval=30,
        )

    @property
    def job_stream_name(self) -> str:
        return self._settings.redis_job_stream

    async def ensure_group(self) -> None:
        try:
            await self._redis.xgroup_create(
                name=self._settings.redis_job_stream,
                groupname=self._settings.redis_job_consumer_group,
                id="0",
                mkstream=True,
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def publish_job(self, payload: dict[str, Any]) -> str:
        await self.ensure_group()
        fields: dict[RedisField, RedisField] = {
            key: str(value) for key, value in payload.items()
        }
        message_id = await self._redis.xadd(self._settings.redis_job_stream, fields)
        return str(message_id)

    async def reclaim_pending(self, *, min_idle_ms: int = 60_000, count: int = 10) -> list[dict[str, Any]]:
        await self.ensure_group()
        try:
            result = await self._redis.xautoclaim(
                name=self._settings.redis_job_stream,
                groupname=self._settings.redis_job_consumer_group,
                consumername=self._settings.redis_consumer_name,
                min_idle_time=min_idle_ms,
                start_id="0-0",
                count=count,
            )
        except ResponseError:
            return []
        # redis-py returns (next_start, messages, deleted_ids) on supported versions
        entries = result[1] if isinstance(result, tuple) and len(result) > 1 else []
        return [
            {"message_id": message_id, "fields": fields}
            for message_id, fields in entries
        ]

    async def read_jobs(self, count: int = 1, block_ms: int = 1_000) -> list[dict[str, Any]]:
        await self.ensure_group()
        reclaimed = await self.reclaim_pending(count=count)
        if reclaimed:
            return reclaimed
        response = await self._redis.xreadgroup(
            groupname=self._settings.redis_job_consumer_group,
            consumername=self._settings.redis_consumer_name,
            streams={self._settings.redis_job_stream: ">"},
            count=count,
            block=block_ms,
        )
        messages: list[dict[str, Any]] = []
        for _, entries in response:
            for message_id, fields in entries:
                messages.append({"message_id": message_id, "fields": fields})
        return messages

    async def acknowledge(self, message_id: str) -> None:
        await self._redis.xack(
            self._settings.redis_job_stream,
            self._settings.redis_job_consumer_group,
            message_id,
        )

    async def dead_letter(self, message_id: str, payload: dict[str, Any]) -> None:
        fields: dict[RedisField, RedisField] = {
            "original_message_id": message_id,
            **{key: str(value) for key, value in payload.items()},
        }
        await self._redis.xadd(self._settings.redis_dead_letter_stream, fields)
        await self.acknowledge(message_id)

    async def close(self) -> None:
        await self._redis.aclose()
