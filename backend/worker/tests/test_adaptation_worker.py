import asyncio
import io
import json
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from docx import Document

from app.core.core import settings
from app.clients.adaptation import AdaptationHttpClient
from app.main import main
from app.schemas.event import AdaptationRequestedEvent
from app.use_cases.adaptation_task import get_adaptation_task_service


class TestAdaptationWorker:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.adaptation_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.resume_id = uuid.uuid4()
        self.vacancy_id = uuid.uuid4()
        self.event = AdaptationRequestedEvent(
            event_type="adaptation.requested",
            data={"adaptation_id": self.adaptation_id, "user_id": self.user_id},
        )

    async def test_real_chain_loads_original_and_saves_review_through_http(self):
        document = Document()
        document.add_paragraph("Original Python resume")
        buffer = io.BytesIO()
        document.save(buffer)
        requests = []
        clients = []
        completions = iter([
            {"matches": [], "gaps": []},
            {"resume_text": "Adapted Python resume"},
            {"passed": False, "issues": ["Unsupported fact"]},
        ])

        def handler(request):
            requests.append(request)
            if request.url.host == "llm.test":
                return httpx.Response(200, json={"choices": [{
                    "finish_reason": "stop", "message": {"content": json.dumps(next(completions))},
                }]})
            assert request.headers["X-Worker-Token"] == "test-worker-token"
            assert request.url.params["user_id"] == str(self.user_id)
            if request.method == "POST":
                assert request.url.path == f"/internal/adaptations/{self.adaptation_id}/claim"
                return httpx.Response(200, json={"resume_id": str(self.resume_id), "vacancy_id": str(self.vacancy_id)})
            if request.url.path == f"/internal/resumes/{self.resume_id}":
                return httpx.Response(200, content=buffer.getvalue())
            if request.url.path == f"/internal/vacancies/{self.vacancy_id}":
                return httpx.Response(200, json={"text": "Python vacancy"})
            assert request.method == "PATCH"
            assert request.url.path == f"/internal/adaptations/{self.adaptation_id}"
            return httpx.Response(200, json={})

        async_client = httpx.AsyncClient

        def create_client(**kwargs):
            client = async_client(transport=httpx.MockTransport(handler), **kwargs)
            clients.append(client)
            return client

        with (
            patch.object(settings, "RESUME_API_URL", "http://resume.test"),
            patch.object(settings, "OPENAI_BASE_URL", "https://llm.test/v1/"),
            patch.object(settings, "OPENAI_API_KEY", "test-key"),
            patch.object(settings, "WORKER_API_TOKEN", "test-worker-token"),
            patch("httpx.AsyncClient", side_effect=create_client),
        ):
            async with get_adaptation_task_service() as service:
                await service.process(self.event)

        assert all(client.is_closed for client in clients)
        assert len(requests) == 7
        result = json.loads(requests[-1].content)
        assert result == {
            "status": "done", "error": None, "result": {
                "resume_text": "Adapted Python resume",
                "review": {"passed": False, "issues": ["Unsupported fact"]},
            },
        }
        for request in requests[3:6]:
            data = json.loads(json.loads(request.content)["messages"][1]["content"])
            assert data["resume"] == "Original Python resume"
            assert data["vacancy"] == "Python vacancy"

    async def test_client_propagates_claim_and_save_http_errors(self, subtests):
        for status in (401, 404, 409, 500):
            for method in ("claim", "save"):
                with subtests.test(status=status, method=method):
                    async_client = httpx.AsyncClient
                    transport = httpx.MockTransport(lambda request: httpx.Response(status))
                    with (
                        patch.object(settings, "OPENAI_API_KEY", "test-key"),
                        patch("httpx.AsyncClient", side_effect=lambda **kwargs: async_client(transport=transport, **kwargs)),
                    ):
                        client = AdaptationHttpClient("http://resume.test")
                        try:
                            with pytest.raises(httpx.HTTPStatusError):
                                if method == "claim":
                                    await client.claim(self.adaptation_id, self.user_id)
                                else:
                                    await client.save(self.adaptation_id, self.user_id, {"status": "failed"})
                        finally:
                            await client.close()

    async def test_startup_error_closes_already_created_clients(self):
        clients = [SimpleNamespace(close=AsyncMock()) for _ in range(3)]
        with (
            patch("app.use_cases.adaptation_task.AdaptationHttpClient", return_value=clients[0]),
            patch("app.use_cases.adaptation_task.ResumeHttpClient", return_value=clients[1]),
            patch("app.use_cases.adaptation_task.VacancyHttpClient", return_value=clients[2]),
            patch("app.use_cases.adaptation_task.LLMHttpClient", side_effect=ValueError("missing key")),
        ):
            with pytest.raises(ValueError):
                async with get_adaptation_task_service():
                    pytest.fail("Must not yield on startup error")
        for client in clients:
            client.close.assert_awaited_once()

    async def test_main_acknowledges_only_after_successful_adaptation(self, subtests):
        for error in (None, ConnectionError(), asyncio.CancelledError()):
            with subtests.test(error=error):
                consumer = SimpleNamespace(
                    consume=AsyncMock(side_effect=[(self.event, b"payload"), asyncio.CancelledError()]),
                    ack=AsyncMock(),
                )
                pipeline = SimpleNamespace(process=AsyncMock())
                adaptation = SimpleNamespace(process=AsyncMock(side_effect=error))
                closed = []

                @asynccontextmanager
                async def context(value):
                    try:
                        yield value
                    finally:
                        closed.append(value)

                with (
                    patch("app.main.get_event_consumer", side_effect=lambda: context(consumer)),
                    patch("app.main.get_pipeline_service", side_effect=lambda: context(pipeline)),
                    patch("app.main.get_adaptation_task_service", side_effect=lambda: context(adaptation)),
                    patch("app.main.asyncio.sleep", new_callable=AsyncMock),
                    patch("app.main.logger.exception"),
                ):
                    with pytest.raises(asyncio.CancelledError):
                        await main()
                assert adaptation in closed
                pipeline.process.assert_not_awaited()
                if error is None:
                    consumer.ack.assert_awaited_once_with(b"payload")
                else:
                    consumer.ack.assert_not_awaited()
