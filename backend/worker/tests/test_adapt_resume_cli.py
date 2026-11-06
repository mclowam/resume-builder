import json
from unittest.mock import patch

import httpx
import pytest

from app.adapt_resume import main
from app.core.core import settings


class TestAdaptResumeCli:
    @pytest.fixture(autouse=True)
    def setup(self, cleanup, tmp_path):
        self.cleanup = cleanup
        self.directory = tmp_path
        self.resume = self.directory / "resume.txt"
        self.vacancy = self.directory / "vacancy.txt"
        self.output = self.directory / "result.json"
        self.resume.write_text("Иван\nРазработчик Python", encoding="utf-8-sig")
        self.vacancy.write_text("Python и Docker", encoding="utf-8")
        self.arguments = [str(self.resume), str(self.vacancy), str(self.output), "--model", "test-model"]

    async def run_cli(self, responses, extra_arguments=()):
        self.requests = []
        responses = iter(responses)

        def handler(request):
            self.requests.append(json.loads(request.content))
            return next(responses)

        client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1/", transport=httpx.MockTransport(handler),
        )
        self.cleanup.push_async_callback(client.aclose)
        with (
            patch.object(settings, "OPENAI_API_KEY", "test-key"),
            patch("app.clients.llm.httpx.AsyncClient", return_value=client),
        ):
            try:
                await main(self.arguments + list(extra_arguments))
            finally:
                assert client.is_closed

    def completion(self, result):
        return httpx.Response(200, json={"choices": [{
            "finish_reason": "stop", "message": {"content": json.dumps(result), "refusal": None},
        }]})

    async def test_writes_full_adaptation_and_rejected_review_as_utf8_json(self):
        await self.run_cli([
            self.completion({"matches": [], "gaps": []}),
            self.completion({"resume_text": "Иван\nPython, Docker"}),
            self.completion({"passed": False, "issues": ["Docker не подтверждён."]}),
        ])

        output = self.output.read_text(encoding="utf-8")
        assert "Иван" in output
        assert json.loads(output) == {
            "resume_text": "Иван\nPython, Docker",
            "review": {"passed": False, "issues": ["Docker не подтверждён."]},
        }
        assert len(self.requests) == 3
        for request in self.requests:
            assert request["model"] == "test-model"
            data = json.loads(request["messages"][1]["content"])
            assert data["resume"] == "Иван\nРазработчик Python"
            assert data["vacancy"] == "Python и Docker"

    async def test_reviews_supplied_resume_without_running_adaptation(self):
        tailored = self.directory / "tailored.txt"
        tailored.write_text("Иван\nPython, Docker", encoding="utf-8")

        await self.run_cli(
            [self.completion({"passed": False, "issues": ["Docker не подтверждён."]})],
            ["--tailored-resume", str(tailored)],
        )

        assert json.loads(self.output.read_text(encoding="utf-8")) == {
            "passed": False, "issues": ["Docker не подтверждён."],
        }
        assert len(self.requests) == 1
        data = json.loads(self.requests[0]["messages"][1]["content"])
        assert data["tailor_result"] == {"resume_text": "Иван\nPython, Docker"}

    async def test_api_error_does_not_write_output(self):
        with pytest.raises(httpx.HTTPStatusError):
            await self.run_cli([httpx.Response(429)])

        assert not self.output.exists()

    async def test_rejects_output_path_pointing_to_input_before_llm_call(self):
        self.arguments[2] = str(self.resume)
        with pytest.raises(SystemExit) as error:
            await main(self.arguments)

        assert error.value.code == 2
        assert self.resume.read_text(encoding="utf-8-sig") == "Иван\nРазработчик Python"
