import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from pydantic import ValidationError

from app.agents.matcher import MatcherAgent
from app.clients.llm import LLMHttpClient


class MatcherTests(unittest.IsolatedAsyncioTestCase):
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
        self.addAsyncCleanup(client.close)
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

        self.assertEqual(actual.model_dump(), result)
        request = self.requests[0]
        self.assertEqual(str(request.url), "https://api.openai.com/v1/chat/completions")
        self.assertEqual(request.headers["Authorization"], "Bearer test-key")
        body = json.loads(request.content)
        self.assertEqual(body["model"], "gpt-4.1-mini")
        self.assertEqual(body["messages"][0]["role"], "system")
        self.assertEqual(body["messages"][1]["role"], "user")
        self.assertEqual(json.loads(body["messages"][1]["content"]), {
            "resume": resume, "vacancy": vacancy,
        })
        self.assertEqual(body["response_format"], {"type": "json_object"})

    async def test_rejects_invalid_results(self):
        for content in ("not json", '{"matches": []}', '{"matches": [], "gaps": ["Docker"]}',
                        '{"matches": [], "gaps": [], "extra": true}'):
            with self.subTest(content=content):
                agent = await self.create_agent(self.completion(content))
                with self.assertRaises(ValidationError):
                    await agent.run("Python", "Docker")

    async def test_rejects_refusal_and_incomplete_results(self):
        for finish_reason, refusal in (("length", None), ("content_filter", None), ("stop", "Refused")):
            agent = await self.create_agent(self.completion('{"matches": [], "gaps": []}', finish_reason, refusal))
            with self.assertRaises(ValueError):
                await agent.run("Python", "Docker")

    async def test_propagates_api_error(self):
        agent = await self.create_agent(httpx.Response(429, json={"error": {"message": "Rate limit"}}))
        with self.assertRaises(httpx.HTTPStatusError):
            await agent.run("Python", "Docker")
        self.assertEqual(len(self.requests), 1)

    async def test_rejects_empty_documents_before_calling_llm(self):
        client = AsyncMock()
        agent = MatcherAgent(client)
        for resume, vacancy in (("", "Python"), ("Python", " \n ")):
            with self.assertRaises(ValueError):
                await agent.run(resume, vacancy)
        client.generate.assert_not_awaited()
