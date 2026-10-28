import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from pydantic import ValidationError

from app.agents.matcher import MatcherAgent
from app.agents.tailor import TailorAgent
from app.clients.llm import LLMHttpClient
from app.schemas.matcher import MatchResult


class TailorTests(unittest.IsolatedAsyncioTestCase):
    async def create_client(self, *responses):
        self.requests = []
        responses = iter(responses)

        def handler(request):
            self.requests.append(request)
            return next(responses)

        http_client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1/", transport=httpx.MockTransport(handler),
        )
        with patch("app.clients.llm.httpx.AsyncClient", return_value=http_client):
            client = LLMHttpClient("https://api.openai.com/v1/", "test-key", "gpt-4.1-mini")
        self.addAsyncCleanup(client.close)
        return client

    def completion(self, content):
        return httpx.Response(200, json={"choices": [{
            "finish_reason": "stop",
            "message": {"content": content, "refusal": None},
        }]})

    async def test_tailors_full_resume_from_matcher_result_through_http_client(self):
        match = {
            "matches": [{"requirement": "Python", "explanation": "Разработка на Python."}],
            "gaps": [{"requirement": "Docker", "explanation": "Опыт Docker не указан."}],
        }
        resume = "  Иван\nРазработчик\nPython: API в компании А, 2023–2025\nОбразование: колледж  "
        vacancy = "  Разработчик Python\nAPI\nDocker  "
        tailored = "  Иван\nРазработчик Python\nРазрабатывал API в компании А, 2023–2025\nОбразование: колледж  "
        client = await self.create_client(
            self.completion(json.dumps(match)),
            self.completion(json.dumps({"resume_text": tailored})),
        )

        match_result = await MatcherAgent(client).run(resume, vacancy)
        result = await TailorAgent(client).run(resume, vacancy, match_result)

        self.assertEqual(result.resume_text, tailored)
        self.assertEqual(match_result.model_dump(), match)
        self.assertEqual(len(self.requests), 2)
        body = json.loads(self.requests[1].content)
        self.assertEqual(json.loads(body["messages"][1]["content"]), {
            "resume": resume, "vacancy": vacancy, "match_result": match,
        })
        self.assertNotEqual(
            body["messages"][0]["content"],
            json.loads(self.requests[0].content)["messages"][0]["content"],
        )

    async def test_rejects_invalid_results(self):
        match_result = MatchResult(matches=[], gaps=[])
        for content in ("not json", "{}", '{"resume_text": null}', '{"resume_text": 42}',
                        '{"resume_text": ["Python"]}', '{"resume_text": ""}',
                        json.dumps({"resume_text": " \n\t "}),
                        '{"resume_text": "Python", "extra": true}'):
            with self.subTest(content=content):
                client = await self.create_client(self.completion(content))
                with self.assertRaises(ValidationError):
                    await TailorAgent(client).run("Python", "Docker", match_result)

    async def test_rejects_empty_documents_before_calling_llm(self):
        client = AsyncMock()
        agent = TailorAgent(client)
        match_result = MatchResult(matches=[], gaps=[])
        for resume, vacancy in (("", "Python"), (" \n ", "Python"),
                                ("Python", ""), ("Python", " \n ")):
            with self.subTest(resume=resume, vacancy=vacancy):
                with self.assertRaises(ValueError):
                    await agent.run(resume, vacancy, match_result)
        client.generate.assert_not_awaited()

    async def test_propagates_api_error(self):
        client = await self.create_client(httpx.Response(429, json={"error": {"message": "Rate limit"}}))
        with self.assertRaises(httpx.HTTPStatusError):
            await TailorAgent(client).run("Python", "Docker", MatchResult(matches=[], gaps=[]))
        self.assertEqual(len(self.requests), 1)
