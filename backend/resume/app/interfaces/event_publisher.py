from typing import Protocol
from app.schemas.event import ResumeUploadedEvent, VacancyUploadedEvent


class IEventPublisher(Protocol):
    async def publish(self, event: ResumeUploadedEvent | VacancyUploadedEvent) -> None:
        pass
