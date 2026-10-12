import json

from redis.asyncio import Redis

from app.schemas.event import ResumeUploadedEvent, VacancyUploadedEvent


class RedisPublisher:
    def __init__(
            self,
            redis_client: Redis,
            queue_name: str,
    ) -> None:
        self._redis = redis_client
        self._queue = queue_name

    async def publish(self, event: ResumeUploadedEvent | VacancyUploadedEvent) -> None:
        payload = {
            "event_type": event.event_type,
            "data": event.model_dump(mode="json", exclude={"event_type"})
        }
        await self._redis.rpush(self._queue, json.dumps(payload))
