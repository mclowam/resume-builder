import asyncio

from app.clients.resume import ResumeHttpClient
from app.clients.vacancy import VacancyHttpClient
from app.schemas.event import Event, ResumeUploadedEvent
from app.services.text_extractor import TextExtractor


class PipelineService:
    def __init__(
            self,
            resume_client: ResumeHttpClient,
            vacancy_client: VacancyHttpClient,
            text_extractor: TextExtractor,
    ):
        self._resume_client = resume_client
        self._vacancy_client = vacancy_client
        self._text_extractor = text_extractor

    async def process(self, event: Event) -> str:
        if isinstance(event, ResumeUploadedEvent):
            data = await self._resume_client.get_resume(
                resume_id=event.data.resume_id,
                user_id=event.data.user_id,
            )
            text = await asyncio.to_thread(self._text_extractor.extract, data)
        else:
            vacancy = await self._vacancy_client.get_vacancy(
                vacancy_id=event.data.vacancy_id,
                user_id=event.data.user_id,
            )
            text = vacancy["text"]

        if not isinstance(text, str) or not text.strip():
            raise ValueError("Document text must not be empty")
        return text
