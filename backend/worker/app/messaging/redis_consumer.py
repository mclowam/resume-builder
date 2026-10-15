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
        self._event_adapter = TypeAdapter(Event)

    async def consume(self, timeout: int = 5) -> Event | None:
        result = await self._redis.blpop(self._queue, timeout=timeout)
        if result is None:
            return None
        return self._event_adapter.validate_json(result[1])
