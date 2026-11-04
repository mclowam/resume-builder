from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from app.agents.critic import CriticAgent
from app.agents.matcher import MatcherAgent
from app.agents.tailor import TailorAgent
from app.clients.adaptation import AdaptationHttpClient
from app.clients.llm import LLMHttpClient
from app.clients.resume import ResumeHttpClient
from app.clients.vacancy import VacancyHttpClient
from app.core.core import settings
from app.services.adaptation_task import AdaptationTaskService
from app.services.document import DocumentService
from app.services.resume_adaptation import ResumeAdaptationService
from app.services.text_extractor import TextExtractor


@asynccontextmanager
async def get_adaptation_task_service() -> AsyncIterator[AdaptationTaskService]:
    async with AsyncExitStack() as stack:
        adaptation_client = AdaptationHttpClient(settings.RESUME_API_URL)
        stack.push_async_callback(adaptation_client.close)
        resume_client = ResumeHttpClient(settings.RESUME_API_URL)
        stack.push_async_callback(resume_client.close)
        vacancy_client = VacancyHttpClient(settings.RESUME_API_URL)
        stack.push_async_callback(vacancy_client.close)
        llm_client = LLMHttpClient(settings.OPENAI_BASE_URL, settings.OPENAI_API_KEY, settings.LLM_MODEL)
        stack.push_async_callback(llm_client.close)
        yield AdaptationTaskService(
            adaptation_client=adaptation_client,
            document_service=DocumentService(resume_client, vacancy_client, TextExtractor()),
            adaptation_service=ResumeAdaptationService(
                MatcherAgent(llm_client), TailorAgent(llm_client), CriticAgent(llm_client),
            ),
        )
