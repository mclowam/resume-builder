from typing import Protocol

from app.schemas.event import Event


class IEventConsumer(Protocol):
    async def consume(self, timeout: int = 5) -> tuple[Event, str | bytes] | None:
        pass

    async def ack(self, payload: str | bytes) -> None:
        pass
