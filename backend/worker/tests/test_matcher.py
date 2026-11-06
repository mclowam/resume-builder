import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from pydantic import ValidationError

from app.agents.matcher import MatcherAgent
from app.clients.llm import LLMHttpClient


class TestMatcher:
    @pytest.fixture(autouse=True)
    def setup(self, cleanup):
        self.cleanup = cleanup

    async def create_agent(self, response):
        self.requests = []

        def handler(request):
            self.requests.append(request)
            return response

        http_client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1/", transport=httpx.MockTransport(handler),
        )
        with patch("app.clients.llm.httpx.AsyncClient", return_value=http_client) as factory:
            client = LLMHttpClient("https://api.openai.com/v1/", "test-key", "gpt-4.1-mini")
        http_client.headers.update(factory.call_args.kwargs["headers"])
        self.cleanup.push_async_callback(client.close)
        return MatcherAgent(client)

    def completion(self, content, finish_reason="stop", refusal=None):
        return httpx.Response(200, json={"choices": [{
            "finish_reason": finish_reason,
            "message": {"content": content, "refusal": refusal},
        }]})

    async def test_matches_full_documents_through_http_client(self):
        result = {
            "matches": [{"requirement": "Python", "explanation": "В резюме указан опыт Python."}],
            "gaps": [{"requirement": "Docker", "explanation": "В резюме опыт Docker не указан."}],
        }
        agent = await self.create_agent(self.completion(json.dumps(result)))
        resume = "  Разработчик\nОпыт Python\nПоследняя строка  "
        vacancy = "  Python\nDocker  "

        actual = await agent.run(resume, vacancy)

        assert actual.model_dump() == result
        request = self.requests[0]
        assert str(request.url) == "https://api.openai.com/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "gpt-4.1-mini"
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["role"] == "user"
        assert json.loads(body["messages"][1]["content"]) == {
            "resume": resume, "vacancy": vacancy,
        }
        assert body["response_format"] == {"type": "json_object"}

    async def test_rejects_invalid_results(self, subtests):
        for content in ("not json", '{"matches": []}', '{"matches": [], "gaps": ["Docker"]}',
                        '{"matches": [], "gaps": [], "extra": true}'):
            with subtests.test(content=content):
                agent = await self.create_agent(self.completion(content))
                with pytest.raises(ValidationError):
                    await agent.run("Python", "Docker")

    async def test_rejects_refusal_and_incomplete_results(self):
        for finish_reason, refusal in (("length", None), ("content_filter", None), ("stop", "Refused")):
            agent = await self.create_agent(self.completion('{"matches": [], "gaps": []}', finish_reason, refusal))
            with pytest.raises(ValueError):
                await agent.run("Python", "Docker")

    async def test_propagates_api_error(self):
        agent = await self.create_agent(httpx.Response(429, json={"error": {"message": "Rate limit"}}))
        with pytest.raises(httpx.HTTPStatusError):
            await agent.run("Python", "Docker")
        assert len(self.requests) == 1

    async def test_rejects_empty_documents_before_calling_llm(self):
        client = AsyncMock()
        agent = MatcherAgent(client)
        for resume, vacancy in (("", "Python"), ("Python", " \n ")):
            with pytest.raises(ValueError):
                await agent.run(resume, vacancy)
        client.generate.assert_not_awaited()
