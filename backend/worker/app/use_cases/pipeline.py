from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from app.clients.embedding import EmbeddingHttpClient
from app.clients.resume import ResumeHttpClient
from app.clients.vacancy import VacancyHttpClient
from app.core.core import settings
from app.services.document import DocumentService
from app.services.pipeline import PipelineService
from app.services.text_extractor import TextExtractor


@asynccontextmanager
async def get_pipeline_service() -> AsyncIterator[PipelineService]:
    async with AsyncExitStack() as stack:
        resume_client = ResumeHttpClient(settings.RESUME_API_URL)
        stack.push_async_callback(resume_client.close)
        vacancy_client = VacancyHttpClient(settings.RESUME_API_URL)
        stack.push_async_callback(vacancy_client.close)
        embedding_client = EmbeddingHttpClient(
            base_url=settings.OPENAI_BASE_URL,
            api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL,
        )
        stack.push_async_callback(embedding_client.close)

        document_service = DocumentService(
            resume_client=resume_client,
            vacancy_client=vacancy_client,
            text_extractor=TextExtractor(),
        )
        yield PipelineService(
            document_service=document_service,
            embedding_client=embedding_client,
        )
