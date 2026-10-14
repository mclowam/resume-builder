import asyncio
import logging

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.interfaces.event_publisher import IEventPublisher
from app.models.outbox import OutboxEvent
from app.schemas.event import ResumeUploadedEvent, VacancyUploadedEvent


logger = logging.getLogger(__name__)


class OutboxDispatcher:
    def __init__(
            self,
            session_factory: async_sessionmaker[AsyncSession],
            event_publisher: IEventPublisher,
            poll_interval: float = 1.0,
            retry_interval: float = 5.0,
            publish_timeout: float = 5.0,
    ):
        self._session_factory = session_factory
        self._event_publisher = event_publisher
        self._poll_interval = poll_interval
        self._retry_interval = retry_interval
        self._publish_timeout = publish_timeout
        self._event_adapter = TypeAdapter(ResumeUploadedEvent | VacancyUploadedEvent)

    async def dispatch_one(self) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                query = (
                    select(OutboxEvent)
                    .order_by(OutboxEvent.created_at, OutboxEvent.id)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                result = await session.execute(query)
                outbox_event = result.scalar_one_or_none()
                if outbox_event is None:
                    return False

                event = self._event_adapter.validate_python(outbox_event.payload)
                await asyncio.wait_for(
                    self._event_publisher.publish(event),
                    timeout=self._publish_timeout,
                )
                await session.delete(outbox_event)

        return True

    async def run(self) -> None:
        while True:
            try:
                if not await self.dispatch_one():
                    await asyncio.sleep(self._poll_interval)
            except Exception:
                logger.exception("Failed to publish outbox event")
                await asyncio.sleep(self._retry_interval)
