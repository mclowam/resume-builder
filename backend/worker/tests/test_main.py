import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call, patch

from app.main import main
from app.core.core import settings


class MainTests(unittest.IsolatedAsyncioTestCase):
    async def test_processes_event_and_closes_clients(self):
        await self.run_worker()

    async def test_continues_after_processing_error(self):
        await self.run_worker(ValueError("Empty text"))

    async def test_continues_after_consume_error(self):
        await self.run_worker(ConnectionError("Redis unavailable"), error_stage="consume")

    async def test_continues_after_ack_error(self):
        await self.run_worker(ConnectionError("Redis unavailable"), error_stage="ack")

    async def test_does_not_ack_cancelled_processing(self):
        await self.run_worker(asyncio.CancelledError())

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

    async def run_worker(self, error=None, error_stage="process"):
        event = SimpleNamespace(event_type="resume.uploaded")
        failed_event = SimpleNamespace(event_type="vacancy.uploaded")
        payload = b"original payload"
        failed_payload = b"failed payload"
        redis = SimpleNamespace(aclose=AsyncMock())
        resume = SimpleNamespace(close=AsyncMock())
        vacancy = SimpleNamespace(close=AsyncMock())
        embedding = SimpleNamespace(close=AsyncMock())
        consumer = SimpleNamespace(
            consume=AsyncMock(side_effect=[None, (event, payload), asyncio.CancelledError()]),
            ack=AsyncMock(),
        )
        document = SimpleNamespace(
            document_type="resume", document_id="resource-id",
            embedding_model="text-embedding-3-small", embedding=[0.1, -0.2],
        )
        pipeline = SimpleNamespace(process=AsyncMock(return_value=document))
        process_calls = [call(event)]
        ack_calls = [call(payload)]
        order = ["process", "ack"]
        if isinstance(error, Exception):
            if error_stage == "consume":
                consumer.consume.side_effect = [error, (event, payload), asyncio.CancelledError()]
                order = ["sleep", "process", "ack"]
            else:
                consumer.consume.side_effect = [
                    (failed_event, failed_payload), (event, payload), asyncio.CancelledError(),
                ]
                process_calls.insert(0, call(failed_event))
                if error_stage == "process":
                    pipeline.process.side_effect = [error, document]
                    order = ["process", "sleep", "process", "ack"]
                else:
                    consumer.ack.side_effect = [error, None]
                    ack_calls.insert(0, call(failed_payload))
                    order = ["process", "ack", "sleep", "process", "ack"]
        elif error is not None:
            pipeline.process.side_effect = error
            ack_calls = []
            order = ["process"]
        calls = Mock()
        calls.attach_mock(pipeline.process, "process")
        calls.attach_mock(consumer.ack, "ack")
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
            patch("app.main.asyncio.sleep", new_callable=AsyncMock) as sleep,
            patch("app.main.logger.exception") as log_error,
        ):
            calls.attach_mock(sleep, "sleep")
            with self.assertRaises(asyncio.CancelledError):
                await main()

        document_factory.assert_called_once_with(
            resume_client=resume, vacancy_client=vacancy, text_extractor=extractor,
        )
        factory.assert_called_once_with(
            document_service=document_service,
            embedding_client=embedding,
        )
        self.assertEqual(pipeline.process.await_args_list, process_calls)
        self.assertEqual(consumer.ack.await_args_list, ack_calls)
        self.assertEqual([item[0] for item in calls.mock_calls], order)
        if isinstance(error, Exception):
            sleep.assert_awaited_once_with(5)
            log_error.assert_called_once()
        else:
            sleep.assert_not_awaited()
            log_error.assert_not_called()
        redis.aclose.assert_awaited_once()
        resume.close.assert_awaited_once()
        vacancy.close.assert_awaited_once()
        embedding.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
