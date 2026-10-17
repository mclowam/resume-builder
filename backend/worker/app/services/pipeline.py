import asyncio

from app.clients.resume import ResumeHttpClient
from app.clients.vacancy import VacancyHttpClient
from app.interfaces.embedding import IEmbeddingClient
from app.schemas.event import Event, ResumeUploadedEvent
from app.schemas.pipeline import DocumentEmbedding
from app.services.text_extractor import TextExtractor


class PipelineService:
    def __init__(
            self,
            resume_client: ResumeHttpClient,
            vacancy_client: VacancyHttpClient,
            text_extractor: TextExtractor,
            embedding_client: IEmbeddingClient,
    ):
        self._resume_client = resume_client
        self._vacancy_client = vacancy_client
        self._text_extractor = text_extractor
        self._embedding_client = embedding_client

    async def process(self, event: Event) -> DocumentEmbedding:
        if isinstance(event, ResumeUploadedEvent):
            document_id = event.data.resume_id
            document_type = "resume"
            data = await self._resume_client.get_resume(
                resume_id=event.data.resume_id,
                user_id=event.data.user_id,
            )
            text = await asyncio.to_thread(self._text_extractor.extract, data)
        else:
            document_id = event.data.vacancy_id
            document_type = "vacancy"
            vacancy = await self._vacancy_client.get_vacancy(
                vacancy_id=event.data.vacancy_id,
                user_id=event.data.user_id,
            )
            text = vacancy["text"]

        if not isinstance(text, str) or not text.strip():
            raise ValueError("Document text must not be empty")
        embedding = await self._embedding_client.embed(text)
        return DocumentEmbedding(
            document_id=document_id,
            user_id=event.data.user_id,
            document_type=document_type,
            text=text,
            embedding=embedding,
            embedding_model=self._embedding_client.model,
        )
