import uuid
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.schemas.event import ResumeUploadedEvent, VacancyUploadedEvent
from app.schemas.embedding import PatchEmbeddingSchema
from app.services.document import DocumentService
from app.services.pipeline import PipelineService


class TestPipelineService:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.resume_client = AsyncMock()
        self.vacancy_client = AsyncMock()
        self.resume_client.get_embedding.return_value = None
        self.vacancy_client.get_embedding.return_value = None
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

    async def test_skips_existing_embeddings(self, subtests):
        self.resume_client.get_resume.return_value = b"resume file"
        self.extractor.extract.return_value = "Full resume text"
        self.vacancy_client.get_vacancy.return_value = {"text": "Full vacancy text"}
        for event, client in (
            (self.resume_event, self.resume_client),
            (self.vacancy_event, self.vacancy_client),
        ):
            for embedding in ([0.1, -0.2], []):
                with subtests.test(event_type=event.event_type, embedding=embedding):
                    client.get_embedding.return_value = embedding

                    assert await self.pipeline.process(event) is None

                    client.get_embedding.assert_awaited_with(self.resource_id, self.user_id)
        self.resume_client.get_resume.assert_not_awaited()
        self.vacancy_client.get_vacancy.assert_not_awaited()
        self.extractor.extract.assert_not_called()
        self.embedding_client.embed.assert_not_awaited()
        self.assert_no_embeddings_saved()

    async def test_repeated_event_does_not_generate_embedding_again(self):
        saved_embedding = None

        async def get_embedding(*args):
            return saved_embedding

        async def set_embedding(*, vacancy_id, user_id, data):
            nonlocal saved_embedding
            saved_embedding = data.embedding

        self.vacancy_client.get_embedding.side_effect = get_embedding
        self.vacancy_client.set_embedding.side_effect = set_embedding
        self.vacancy_client.get_vacancy.return_value = {"text": "Full vacancy text"}

        first = await self.pipeline.process(self.vacancy_event)
        second = await self.pipeline.process(self.vacancy_event)

        assert first.embedding == [0.1, -0.2]
        assert second is None
        self.embedding_client.embed.assert_awaited_once_with("Full vacancy text")
        self.vacancy_client.get_vacancy.assert_awaited_once()
        self.vacancy_client.set_embedding.assert_awaited_once()

    async def test_propagates_embedding_lookup_error(self, subtests):
        for event, client in (
            (self.resume_event, self.resume_client),
            (self.vacancy_event, self.vacancy_client),
        ):
            with subtests.test(event_type=event.event_type):
                error = httpx.ReadTimeout("Timed out")
                client.get_embedding.side_effect = error

                with pytest.raises(httpx.ReadTimeout) as raised:
                    await self.pipeline.process(event)

                assert raised.value is error
        self.resume_client.get_resume.assert_not_awaited()
        self.vacancy_client.get_vacancy.assert_not_awaited()
        self.embedding_client.embed.assert_not_awaited()
        self.assert_no_embeddings_saved()

    async def test_extracts_full_resume_text(self):
        self.resume_client.get_resume.return_value = b"resume file"
        self.extractor.extract.return_value = "  Разработчик\nPython\nОпыт работы  "

        document = await self.pipeline.process(self.resume_event)

        assert document.text == "  Разработчик\nPython\nОпыт работы  "
        assert document.document_id == self.resource_id
        assert document.user_id == self.user_id
        assert document.document_type == "resume"
        assert document.embedding == [0.1, -0.2]
        assert document.embedding_model == "text-embedding-3-small"
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

        assert document.text == "  Backend developer\nPython, PostgreSQL  "
        assert document.document_id == self.resource_id
        assert document.user_id == self.user_id
        assert document.document_type == "vacancy"
        assert document.embedding == [0.1, -0.2]
        assert document.embedding_model == "text-embedding-3-small"
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

    async def test_rejects_empty_vacancy_text(self, subtests):
        for text in ("", " \t\n "):
            with subtests.test(text=text):
                self.vacancy_client.get_vacancy.return_value = {"text": text}

                with pytest.raises(ValueError):
                    await self.pipeline.process(self.vacancy_event)
        self.embedding_client.embed.assert_not_awaited()
        self.assert_no_embeddings_saved()

    async def test_rejects_empty_resume_text(self, subtests):
        self.resume_client.get_resume.return_value = b"resume file"
        for text in ("", " \t\n "):
            with subtests.test(text=text):
                self.extractor.extract.return_value = text

                with pytest.raises(ValueError):
                    await self.pipeline.process(self.resume_event)
        self.embedding_client.embed.assert_not_awaited()
        self.assert_no_embeddings_saved()

    async def test_propagates_embedding_error(self):
        self.vacancy_client.get_vacancy.return_value = {"text": "Full text"}
        error = ValueError("Invalid embedding response")
        self.embedding_client.embed.side_effect = error

        with pytest.raises(ValueError) as raised:
            await self.pipeline.process(self.vacancy_event)

        assert raised.value is error
        self.assert_no_embeddings_saved()

    async def test_propagates_extraction_error(self):
        self.resume_client.get_resume.return_value = b"invalid file"
        error = ValueError("Invalid resume file")
        self.extractor.extract.side_effect = error

        with pytest.raises(ValueError) as raised:
            await self.pipeline.process(self.resume_event)

        assert raised.value is error
        self.assert_no_embeddings_saved()

    async def test_propagates_http_errors(self, subtests):
        for event, method in (
            (self.resume_event, self.resume_client.get_resume),
            (self.vacancy_event, self.vacancy_client.get_vacancy),
        ):
            with subtests.test(event_type=event.event_type):
                request = httpx.Request("GET", "http://resume/internal/resource")
                response = httpx.Response(403, request=request)
                error = httpx.HTTPStatusError(
                    "Forbidden", request=request, response=response,
                )
                method.side_effect = error

                with pytest.raises(httpx.HTTPStatusError) as raised:
                    await self.pipeline.process(event)

                assert raised.value is error
        self.extractor.extract.assert_not_called()
        self.assert_no_embeddings_saved()

    async def test_propagates_embedding_save_errors(self, subtests):
        self.resume_client.get_resume.return_value = b"resume file"
        self.extractor.extract.return_value = "Full text"
        self.vacancy_client.get_vacancy.return_value = {"text": "Full text"}
        for event, method in (
            (self.resume_event, self.resume_client.set_embedding),
            (self.vacancy_event, self.vacancy_client.set_embedding),
        ):
            with subtests.test(event_type=event.event_type):
                request = httpx.Request("PATCH", "http://resume/internal/resource")
                response = httpx.Response(500, request=request)
                error = httpx.HTTPStatusError(
                    "Save failed", request=request, response=response,
                )
                method.side_effect = error

                with pytest.raises(httpx.HTTPStatusError) as raised:
                    await self.pipeline.process(event)

                assert raised.value is error
                method.assert_awaited_once()

    def assert_no_embeddings_saved(self):
        self.resume_client.set_embedding.assert_not_awaited()
        self.vacancy_client.set_embedding.assert_not_awaited()
