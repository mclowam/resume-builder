import unittest
import uuid
from unittest.mock import AsyncMock, Mock

import httpx

from app.schemas.event import ResumeUploadedEvent, VacancyUploadedEvent
from app.services.pipeline import PipelineService


class PipelineServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.resume_client = AsyncMock()
        self.vacancy_client = AsyncMock()
        self.extractor = Mock()
        self.pipeline = PipelineService(
            self.resume_client, self.vacancy_client, self.extractor,
        )
        self.resource_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.resume_event = ResumeUploadedEvent(
            event_type="resume.uploaded",
            data={"resume_id": self.resource_id, "user_id": self.user_id},
        )
        self.vacancy_event = VacancyUploadedEvent(
            event_type="vacancy.uploaded",
            data={"vacancy_id": self.resource_id, "user_id": self.user_id},
        )

    async def test_extracts_full_resume_text(self):
        self.resume_client.get_resume.return_value = b"resume file"
        self.extractor.extract.return_value = "  Разработчик\nPython\nОпыт работы  "

        text = await self.pipeline.process(self.resume_event)

        self.assertEqual(text, "  Разработчик\nPython\nОпыт работы  ")
        self.resume_client.get_resume.assert_awaited_once_with(
            resume_id=self.resource_id, user_id=self.user_id,
        )
        self.extractor.extract.assert_called_once_with(b"resume file")
        self.vacancy_client.get_vacancy.assert_not_awaited()

    async def test_returns_full_vacancy_text(self):
        self.vacancy_client.get_vacancy.return_value = {
            "text": "  Backend developer\nPython, PostgreSQL  ",
        }

        text = await self.pipeline.process(self.vacancy_event)

        self.assertEqual(text, "  Backend developer\nPython, PostgreSQL  ")
        self.vacancy_client.get_vacancy.assert_awaited_once_with(
            vacancy_id=self.resource_id, user_id=self.user_id,
        )
        self.resume_client.get_resume.assert_not_awaited()
        self.extractor.extract.assert_not_called()

    async def test_rejects_empty_vacancy_text(self):
        for text in ("", " \t\n "):
            with self.subTest(text=text):
                self.vacancy_client.get_vacancy.return_value = {"text": text}

                with self.assertRaises(ValueError):
                    await self.pipeline.process(self.vacancy_event)

    async def test_rejects_empty_resume_text(self):
        self.resume_client.get_resume.return_value = b"resume file"
        for text in ("", " \t\n "):
            with self.subTest(text=text):
                self.extractor.extract.return_value = text

                with self.assertRaises(ValueError):
                    await self.pipeline.process(self.resume_event)

    async def test_propagates_extraction_error(self):
        self.resume_client.get_resume.return_value = b"invalid file"
        error = ValueError("Invalid resume file")
        self.extractor.extract.side_effect = error

        with self.assertRaises(ValueError) as raised:
            await self.pipeline.process(self.resume_event)

        self.assertIs(raised.exception, error)

    async def test_propagates_http_errors(self):
        for event, method in (
            (self.resume_event, self.resume_client.get_resume),
            (self.vacancy_event, self.vacancy_client.get_vacancy),
        ):
            with self.subTest(event_type=event.event_type):
                request = httpx.Request("GET", "http://resume/internal/resource")
                response = httpx.Response(403, request=request)
                error = httpx.HTTPStatusError(
                    "Forbidden", request=request, response=response,
                )
                method.side_effect = error

                with self.assertRaises(httpx.HTTPStatusError) as raised:
                    await self.pipeline.process(event)

                self.assertIs(raised.exception, error)
        self.extractor.extract.assert_not_called()


if __name__ == "__main__":
    unittest.main()
