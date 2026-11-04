from typing import Protocol
from app.schemas.event import ResumeUploadedEvent, VacancyUploadedEvent, AdaptationRequestedEvent


class IEventPublisher(Protocol):
    async def publish(self, event: ResumeUploadedEvent | VacancyUploadedEvent | AdaptationRequestedEvent) -> None:
        pass
