from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.asyncio import Redis

from app.core.core import settings
from app.interfaces.event_consumer import IEventConsumer
from app.messaging.redis_consumer import RedisConsumer


@asynccontextmanager
async def get_event_consumer() -> AsyncIterator[IEventConsumer]:
    redis_client = Redis.from_url(settings.REDIS_URL)
    try:
        yield RedisConsumer(redis_client, settings.REDIS_QUEUE_NAME)
    finally:
        await redis_client.aclose()
