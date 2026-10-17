import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.main import main
from app.core.core import settings


class MainTests(unittest.IsolatedAsyncioTestCase):
    async def test_processes_event_and_closes_clients(self):
        await self.run_worker(asyncio.CancelledError())

    async def test_closes_clients_on_processing_error(self):
        await self.run_worker(ValueError("Empty text"))

    async def test_closes_created_clients_on_startup_error(self):
        redis = SimpleNamespace(aclose=AsyncMock())
        resume = SimpleNamespace(close=AsyncMock())
        with (
            patch("app.use_cases.event_consumer.Redis.from_url", return_value=redis),
            patch("app.use_cases.pipeline.ResumeHttpClient", return_value=resume),
            patch("app.use_cases.pipeline.VacancyHttpClient", side_effect=ValueError("Invalid URL")),
        ):
            with self.assertRaises(ValueError):
                await main()

        resume.close.assert_awaited_once()
        redis.aclose.assert_awaited_once()

    async def test_missing_api_key_does_not_consume_and_closes_clients(self):
        for api_key in (None, "", " \t "):
            with self.subTest(api_key=api_key):
                redis = SimpleNamespace(aclose=AsyncMock())
                resume = SimpleNamespace(close=AsyncMock())
                vacancy = SimpleNamespace(close=AsyncMock())
                consumer = SimpleNamespace(consume=AsyncMock())
                with (
                    patch.object(settings, "OPENAI_API_KEY", api_key),
                    patch("app.use_cases.event_consumer.Redis.from_url", return_value=redis),
                    patch("app.use_cases.event_consumer.RedisConsumer", return_value=consumer),
                    patch("app.use_cases.pipeline.ResumeHttpClient", return_value=resume),
                    patch("app.use_cases.pipeline.VacancyHttpClient", return_value=vacancy),
                ):
                    with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"):
                        await main()

                consumer.consume.assert_not_awaited()
                redis.aclose.assert_awaited_once()
                resume.close.assert_awaited_once()
                vacancy.close.assert_awaited_once()

    async def run_worker(self, error):
        event = SimpleNamespace(event_type="resume.uploaded")
        redis = SimpleNamespace(aclose=AsyncMock())
        resume = SimpleNamespace(close=AsyncMock())
        vacancy = SimpleNamespace(close=AsyncMock())
        embedding = SimpleNamespace(close=AsyncMock())
        consumer = SimpleNamespace(consume=AsyncMock(side_effect=[None, event, asyncio.CancelledError()]))
        document = SimpleNamespace(
            document_type="resume", document_id="resource-id",
            embedding_model="text-embedding-3-small", embedding=[0.1, -0.2],
        )
        pipeline = SimpleNamespace(process=AsyncMock(return_value=document))
        if isinstance(error, ValueError):
            pipeline.process.side_effect = error
        extractor = Mock()
        document_service = Mock()

        with (
            patch("app.use_cases.event_consumer.Redis.from_url", return_value=redis),
            patch("app.use_cases.pipeline.ResumeHttpClient", return_value=resume),
            patch("app.use_cases.pipeline.VacancyHttpClient", return_value=vacancy),
            patch("app.use_cases.pipeline.EmbeddingHttpClient", return_value=embedding),
            patch("app.use_cases.event_consumer.RedisConsumer", return_value=consumer),
            patch("app.use_cases.pipeline.TextExtractor", return_value=extractor),
            patch("app.use_cases.pipeline.DocumentService", return_value=document_service) as document_factory,
            patch("app.use_cases.pipeline.PipelineService", return_value=pipeline) as factory,
        ):
            with self.assertRaises(type(error)):
                await main()

        document_factory.assert_called_once_with(
            resume_client=resume, vacancy_client=vacancy, text_extractor=extractor,
        )
        factory.assert_called_once_with(
            document_service=document_service,
            embedding_client=embedding,
        )
        pipeline.process.assert_awaited_once_with(event)
        redis.aclose.assert_awaited_once()
        resume.close.assert_awaited_once()
        vacancy.close.assert_awaited_once()
        embedding.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
