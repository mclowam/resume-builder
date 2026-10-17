import unittest
import uuid
from unittest.mock import AsyncMock, Mock

import httpx

from app.schemas.event import ResumeUploadedEvent, VacancyUploadedEvent
from app.schemas.embedding import PatchEmbeddingSchema
from app.services.document import DocumentService
from app.services.pipeline import PipelineService


class PipelineServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.resume_client = AsyncMock()
        self.vacancy_client = AsyncMock()
        self.extractor = Mock()
        self.embedding_client = AsyncMock()
        self.embedding_client.model = "text-embedding-3-small"
        self.embedding_client.embed.return_value = [0.1, -0.2]
        self.document_service = DocumentService(
            self.resume_client, self.vacancy_client, self.extractor,
        )
        self.pipeline = PipelineService(self.document_service, self.embedding_client)
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

        document = await self.pipeline.process(self.resume_event)

        self.assertEqual(document.text, "  Разработчик\nPython\nОпыт работы  ")
        self.assertEqual(document.document_id, self.resource_id)
        self.assertEqual(document.user_id, self.user_id)
        self.assertEqual(document.document_type, "resume")
        self.assertEqual(document.embedding, [0.1, -0.2])
        self.assertEqual(document.embedding_model, "text-embedding-3-small")
        self.embedding_client.embed.assert_awaited_once_with(document.text)
        self.resume_client.get_resume.assert_awaited_once_with(
            resume_id=self.resource_id, user_id=self.user_id,
        )
        self.extractor.extract.assert_called_once_with(b"resume file")
        self.vacancy_client.get_vacancy.assert_not_awaited()
        self.resume_client.set_embedding.assert_awaited_once_with(
            resume_id=self.resource_id, user_id=self.user_id,
            data=PatchEmbeddingSchema(embedding=[0.1, -0.2]),
        )
        self.vacancy_client.set_embedding.assert_not_awaited()

    async def test_returns_full_vacancy_text(self):
        self.vacancy_client.get_vacancy.return_value = {
            "text": "  Backend developer\nPython, PostgreSQL  ",
        }

        document = await self.pipeline.process(self.vacancy_event)

        self.assertEqual(document.text, "  Backend developer\nPython, PostgreSQL  ")
        self.assertEqual(document.document_id, self.resource_id)
        self.assertEqual(document.user_id, self.user_id)
        self.assertEqual(document.document_type, "vacancy")
        self.assertEqual(document.embedding, [0.1, -0.2])
        self.assertEqual(document.embedding_model, "text-embedding-3-small")
        self.embedding_client.embed.assert_awaited_once_with(document.text)
        self.vacancy_client.get_vacancy.assert_awaited_once_with(
            vacancy_id=self.resource_id, user_id=self.user_id,
        )
        self.resume_client.get_resume.assert_not_awaited()
        self.extractor.extract.assert_not_called()
        self.vacancy_client.set_embedding.assert_awaited_once_with(
            vacancy_id=self.resource_id, user_id=self.user_id,
            data=PatchEmbeddingSchema(embedding=[0.1, -0.2]),
        )
        self.resume_client.set_embedding.assert_not_awaited()

    async def test_rejects_empty_vacancy_text(self):
        for text in ("", " \t\n "):
            with self.subTest(text=text):
                self.vacancy_client.get_vacancy.return_value = {"text": text}

                with self.assertRaises(ValueError):
                    await self.pipeline.process(self.vacancy_event)
        self.embedding_client.embed.assert_not_awaited()
        self.assert_no_embeddings_saved()

    async def test_rejects_empty_resume_text(self):
        self.resume_client.get_resume.return_value = b"resume file"
        for text in ("", " \t\n "):
            with self.subTest(text=text):
                self.extractor.extract.return_value = text

                with self.assertRaises(ValueError):
                    await self.pipeline.process(self.resume_event)
        self.embedding_client.embed.assert_not_awaited()
        self.assert_no_embeddings_saved()

    async def test_propagates_embedding_error(self):
        self.vacancy_client.get_vacancy.return_value = {"text": "Full text"}
        error = ValueError("Invalid embedding response")
        self.embedding_client.embed.side_effect = error

        with self.assertRaises(ValueError) as raised:
            await self.pipeline.process(self.vacancy_event)

        self.assertIs(raised.exception, error)
        self.assert_no_embeddings_saved()

    async def test_propagates_extraction_error(self):
        self.resume_client.get_resume.return_value = b"invalid file"
        error = ValueError("Invalid resume file")
        self.extractor.extract.side_effect = error

        with self.assertRaises(ValueError) as raised:
            await self.pipeline.process(self.resume_event)

        self.assertIs(raised.exception, error)
        self.assert_no_embeddings_saved()

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
        self.assert_no_embeddings_saved()

    async def test_propagates_embedding_save_errors(self):
        self.resume_client.get_resume.return_value = b"resume file"
        self.extractor.extract.return_value = "Full text"
        self.vacancy_client.get_vacancy.return_value = {"text": "Full text"}
        for event, method in (
            (self.resume_event, self.resume_client.set_embedding),
            (self.vacancy_event, self.vacancy_client.set_embedding),
        ):
            with self.subTest(event_type=event.event_type):
                request = httpx.Request("PATCH", "http://resume/internal/resource")
                response = httpx.Response(500, request=request)
                error = httpx.HTTPStatusError(
                    "Save failed", request=request, response=response,
                )
                method.side_effect = error

                with self.assertRaises(httpx.HTTPStatusError) as raised:
                    await self.pipeline.process(event)

                self.assertIs(raised.exception, error)
                method.assert_awaited_once()

    def assert_no_embeddings_saved(self):
        self.resume_client.set_embedding.assert_not_awaited()
        self.vacancy_client.set_embedding.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
