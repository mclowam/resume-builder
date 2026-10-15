from typing import Protocol

from app.schemas.event import Event


class IEventConsumer(Protocol):
    async def consume(self, timeout: int = 5) -> Event | None:
        pass
