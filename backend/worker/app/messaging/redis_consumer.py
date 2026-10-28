from pydantic import TypeAdapter
from redis.asyncio import Redis
from app.schemas.event import Event


class RedisConsumer:
    def __init__(
            self,
            redis_client: Redis,
            queue_name: str,
    ) -> None:
        self._redis = redis_client
        self._queue = queue_name
        self._processing_queue = f"{queue_name}:processing"
        self._event_adapter = TypeAdapter(Event)

    async def consume(self, timeout: int = 5) -> tuple[Event, str | bytes] | None:
        result = await self._redis.blmove(
            self._queue, self._processing_queue, timeout=timeout,
            src="LEFT", dest="RIGHT",
        )
        if result is None:
            return None
        return self._event_adapter.validate_json(result), result

    async def ack(self, payload: str | bytes) -> None:
        await self._redis.lrem(self._processing_queue, 1, payload)
