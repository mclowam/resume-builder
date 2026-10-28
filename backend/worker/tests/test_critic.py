import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from pydantic import ValidationError

from app.agents.critic import CriticAgent
from app.agents.matcher import MatcherAgent
from app.agents.tailor import TailorAgent
from app.clients.llm import LLMHttpClient
from app.schemas.tailor import TailorResult


class CriticTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_reviews_tailor_result_after_matcher_through_http_client(self):
        resume = "  Иван\nРазработчик\nPython: API в компании А, 2023–2025\nКолледж  "
        vacancy = "  Разработчик Python\nAPI\nDocker  "
        tailored = "  Иван\nРазработчик Python\nРазрабатывал API в компании А, 2023–2025\nКолледж  "
        client = await self.create_client(
            self.completion(json.dumps({
                "matches": [{"requirement": "Python", "explanation": "Разработка API на Python."}],
                "gaps": [{"requirement": "Docker", "explanation": "Опыт Docker не указан."}],
            })),
            self.completion(json.dumps({"resume_text": tailored})),
            self.completion('{"passed": true, "issues": []}'),
        )

        match_result = await MatcherAgent(client).run(resume, vacancy)
        tailor_result = await TailorAgent(client).run(resume, vacancy, match_result)
        result = await CriticAgent(client).run(resume, vacancy, tailor_result)

        self.assertEqual(result.model_dump(), {"passed": True, "issues": []})
        self.assertEqual(tailor_result.resume_text, tailored)
        self.assertEqual(len(self.requests), 3)
        body = json.loads(self.requests[2].content)
        self.assertEqual(json.loads(body["messages"][1]["content"]), {
            "resume": resume, "vacancy": vacancy, "tailor_result": {"resume_text": tailored},
        })
        self.assertNotEqual(
            body["messages"][0]["content"],
            json.loads(self.requests[1].content)["messages"][0]["content"],
        )

    async def test_returns_failed_review_with_issues(self):
        review = {
            "passed": False,
            "issues": ["Добавлен Docker, который не указан в исходном резюме. Удалить неподтверждённый навык."],
        }
        client = await self.create_client(self.completion(json.dumps(review)))

        result = await CriticAgent(client).run("Python", "Python и Docker", TailorResult(resume_text="Python, Docker"))

        self.assertEqual(result.model_dump(), review)

    async def test_rejects_invalid_results(self):
        for content in ("not json", "{}", '{"passed": true}', '{"issues": []}',
                        '{"passed": "true", "issues": []}', '{"passed": 1, "issues": []}',
                        '{"passed": null, "issues": []}', '{"passed": true, "issues": ["Problem"]}',
                        '{"passed": false, "issues": []}', '{"passed": false, "issues": [""]}',
                        json.dumps({"passed": False, "issues": [" \n\t "]}),
                        '{"passed": false, "issues": [42]}', '{"passed": false, "issues": "Problem"}',
                        '{"passed": true, "issues": [], "extra": true}'):
            with self.subTest(content=content):
                client = await self.create_client(self.completion(content))
                with self.assertRaises(ValidationError):
                    await CriticAgent(client).run("Python", "Docker", TailorResult(resume_text="Python"))

    async def test_rejects_empty_documents_before_calling_llm(self):
        client = AsyncMock()
        agent = CriticAgent(client)
        tailor_result = TailorResult(resume_text="Python")
        for resume, vacancy in (("", "Python"), (" \n ", "Python"),
                                ("Python", ""), ("Python", " \n ")):
            with self.subTest(resume=resume, vacancy=vacancy):
                with self.assertRaises(ValueError):
                    await agent.run(resume, vacancy, tailor_result)
        client.generate.assert_not_awaited()

    async def test_propagates_api_error(self):
        client = await self.create_client(httpx.Response(429, json={"error": {"message": "Rate limit"}}))
        with self.assertRaises(httpx.HTTPStatusError):
            await CriticAgent(client).run("Python", "Docker", TailorResult(resume_text="Python"))
        self.assertEqual(len(self.requests), 1)
