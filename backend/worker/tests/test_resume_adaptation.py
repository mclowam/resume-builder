import json
import unittest
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from app.agents.critic import CriticAgent
from app.agents.matcher import MatcherAgent
from app.agents.tailor import TailorAgent
from app.clients.llm import LLMHttpClient
from app.services.resume_adaptation import ResumeAdaptationService


class ResumeAdaptationTests(unittest.IsolatedAsyncioTestCase):
    async def create_service(self, *responses):
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
        return ResumeAdaptationService(MatcherAgent(client), TailorAgent(client), CriticAgent(client))

    def completion(self, result):
        return httpx.Response(200, json={"choices": [{
            "finish_reason": "stop",
            "message": {"content": json.dumps(result), "refusal": None},
        }]})

    async def test_runs_agents_in_order_with_original_documents(self):
        resume = "  Иван\nPython: API в компании А, 2023–2025\nКолледж  "
        vacancy = "  Разработчик Python\nDocker  "
        match = {
            "matches": [{"requirement": "Python", "explanation": "Разработка API на Python."}],
            "gaps": [{"requirement": "Docker", "explanation": "Опыт Docker не указан."}],
        }
        tailored = "  Иван\nРазработчик Python\nРазрабатывал API в компании А, 2023–2025\nКолледж  "
        service = await self.create_service(
            self.completion(match),
            self.completion({"resume_text": tailored}),
            self.completion({"passed": True, "issues": []}),
        )

        result = await service.run(resume, vacancy)

        self.assertEqual(result.model_dump(), {
            "resume_text": tailored, "review": {"passed": True, "issues": []},
        })
        payloads = [json.loads(json.loads(request.content)["messages"][1]["content"]) for request in self.requests]
        self.assertEqual(payloads, [
            {"resume": resume, "vacancy": vacancy},
            {"resume": resume, "vacancy": vacancy, "match_result": match},
            {"resume": resume, "vacancy": vacancy, "tailor_result": {"resume_text": tailored}},
        ])

    async def test_returns_rejected_review_without_retrying(self):
        service = await self.create_service(
            self.completion({"matches": [], "gaps": []}),
            self.completion({"resume_text": "Python, Docker"}),
            self.completion({"passed": False, "issues": ["Docker отсутствует в исходном резюме."]}),
        )

        result = await service.run("Python", "Python и Docker")

        self.assertEqual(result.model_dump(), {
            "resume_text": "Python, Docker",
            "review": {"passed": False, "issues": ["Docker отсутствует в исходном резюме."]},
        })
        self.assertEqual(len(self.requests), 3)

    async def test_stops_after_error_at_any_stage(self):
        for stage in range(3):
            for error in ("http", "validation"):
                with self.subTest(stage=stage, error=error):
                    responses = [
                        self.completion({"matches": [], "gaps": []}),
                        self.completion({"resume_text": "Python"}),
                        self.completion({"passed": True, "issues": []}),
                    ]
                    if error == "http":
                        responses[stage] = httpx.Response(429, json={"error": {"message": "Rate limit"}})
                        expected = httpx.HTTPStatusError
                    else:
                        responses[stage] = self.completion({})
                        expected = ValidationError
                    service = await self.create_service(*responses)

                    with self.assertRaises(expected):
                        await service.run("Python", "Python")

                    self.assertEqual(len(self.requests), stage + 1)

    async def test_rejects_empty_documents_before_http_request(self):
        service = await self.create_service()
        for resume, vacancy in (("", "Python"), (" \n ", "Python"),
                                ("Python", ""), ("Python", " \n ")):
            with self.subTest(resume=resume, vacancy=vacancy):
                with self.assertRaises(ValueError):
                    await service.run(resume, vacancy)
        self.assertEqual(self.requests, [])
