import asyncio

from app.clients.resume import ResumeHttpClient
from app.clients.vacancy import VacancyHttpClient
from app.schemas.embedding import PatchEmbeddingSchema
from app.schemas.event import Event, ResumeUploadedEvent
from app.schemas.pipeline import DocumentText
from app.services.text_extractor import TextExtractor


class DocumentService:
    def __init__(
            self,
            resume_client: ResumeHttpClient,
            vacancy_client: VacancyHttpClient,
            text_extractor: TextExtractor,
    ):
        self._resume_client = resume_client
        self._vacancy_client = vacancy_client
        self._text_extractor = text_extractor

    async def get_embedding(self, event: Event) -> list[float] | None:
        if isinstance(event, ResumeUploadedEvent):
            return await self._resume_client.get_embedding(event.data.resume_id, event.data.user_id)
        return await self._vacancy_client.get_embedding(event.data.vacancy_id, event.data.user_id)

    async def get_document(self, event: Event) -> DocumentText:
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
        return DocumentText(
            document_id=document_id,
            user_id=event.data.user_id,
            document_type=document_type,
            text=text,
        )

    async def set_embedding(self, document: DocumentText, embedding: list[float]) -> None:
        data = PatchEmbeddingSchema(embedding=embedding)
        if document.document_type == "resume":
            await self._resume_client.set_embedding(
                resume_id=document.document_id, user_id=document.user_id, data=data,
            )
        else:
            await self._vacancy_client.set_embedding(
                vacancy_id=document.document_id, user_id=document.user_id, data=data,
            )
