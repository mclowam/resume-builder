from fastapi import Request

from app.core.config import settings
from app.interfaces.event_publisher import IEventPublisher
from app.messaging.redis_publisher import RedisPublisher


def get_event_publisher(request: Request) -> IEventPublisher:
    return RedisPublisher(
        redis_client=request.app.state.redis,
        queue_name=settings.REDIS_QUEUE_NAME,
    )
