import json
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI

from app.api.internal import api_v1_router as internal_router
from app.api.resume import api_v1_router as resume_router
from app.api.vacancy import api_v1_router as vacancy_router
from app.core.config import settings
from app.schemas.vacancy import VacancyResponseSchema
from app.services.resume import ResumeService
from app.services.vacancy import VacancyService
from app.use_cases.resume import get_resume_service
from app.use_cases.vacancy import get_vacancy_service


class InternalTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_id = uuid.uuid4()
        self.resume = SimpleNamespace(
            id=uuid.uuid4(), user_id=self.user_id,
            file_url="http://minio/resumes/resume.pdf",
            embedding=[0.1, -0.2], created_at=datetime.now(timezone.utc),
        )
        self.vacancy = VacancyResponseSchema(
            id=uuid.uuid4(), user_id=self.user_id, text="Python developer",
        )
        self.resume_repository = SimpleNamespace(
            get_by_id=AsyncMock(return_value=self.resume),
            set_embedding=AsyncMock(return_value=self.resume),
        )
        self.vacancy_repository = SimpleNamespace(
            get_by_id=AsyncMock(return_value=self.vacancy),
            set_embedding=AsyncMock(return_value=self.vacancy),
        )
        self.storage = SimpleNamespace(
            get_key=Mock(return_value="resume.pdf"),
            get_bytes=AsyncMock(return_value=(b"original file bytes", "application/pdf")),
        )
        self.app = FastAPI()
        self.app.include_router(internal_router)
        self.app.include_router(resume_router)
        self.app.include_router(vacancy_router)
        self.app.dependency_overrides[get_resume_service] = lambda: ResumeService(
            self.resume_repository, self.storage,
        )
        self.app.dependency_overrides[get_vacancy_service] = lambda: VacancyService(
            self.vacancy_repository,
        )
        self.paths = (
            f"/internal/resumes/{self.resume.id}",
            f"/internal/vacancies/{self.vacancy.id}",
        )
        self.embedding_paths = tuple(f"{path}/embedding" for path in self.paths)
        token_patch = patch.object(settings, "WORKER_API_TOKEN", "test-worker-token")
        token_patch.start()
        self.addCleanup(token_patch.stop)

    async def request(self, path, token="test-worker-token", query=None, method="GET", payload=None):
        messages = []
        headers = [] if token is None else [(b"x-worker-token", token.encode())]
        if payload is not None:
            headers.append((b"content-type", b"application/json"))

        async def receive():
            body = b"" if payload is None else json.dumps(payload).encode()
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        await self.app({
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": method, "scheme": "http", "path": path, "root_path": "",
            "query_string": (f"user_id={self.user_id}" if query is None else query).encode(),
            "headers": headers,
            "server": ("test", 80), "client": ("test", 1234),
        }, receive, send)
        response = next(message for message in messages if message["type"] == "http.response.start")
        body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
        return response["status"], dict(response["headers"]), body

    async def test_invalid_token_rejected_before_resource_access(self):
        for path in self.paths + self.embedding_paths:
            for token in (None, "", "wrong-token"):
                with self.subTest(path=path, token=token):
                    status, _, _ = await self.request(path, token=token)
                    self.assertEqual(status, 401)
        self.resume_repository.get_by_id.assert_not_awaited()
        self.vacancy_repository.get_by_id.assert_not_awaited()
        self.storage.get_bytes.assert_not_awaited()

    async def test_disabled_worker_access(self):
        for expected in (None, ""):
            with patch.object(settings, "WORKER_API_TOKEN", expected):
                for path in self.paths + self.embedding_paths:
                    with self.subTest(path=path, expected=expected):
                        status, _, _ = await self.request(path)
                        self.assertEqual(status, 503)
        self.resume_repository.get_by_id.assert_not_awaited()
        self.vacancy_repository.get_by_id.assert_not_awaited()

    async def test_worker_receives_original_file(self):
        status, headers, body = await self.request(self.paths[0])
        self.assertEqual(status, 200)
        self.assertEqual(body, b"original file bytes")
        self.assertEqual(headers[b"content-type"], b"application/pdf")
        self.assertEqual(headers[b"content-disposition"], b"attachment; filename*=UTF-8''resume.pdf")
        self.resume_repository.get_by_id.assert_awaited_once_with(self.resume.id)
        self.storage.get_bytes.assert_awaited_once_with("resume.pdf")

    async def test_worker_receives_vacancy(self):
        status, _, body = await self.request(self.paths[1])
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), self.vacancy.model_dump(mode="json"))
        self.vacancy_repository.get_by_id.assert_awaited_once_with(self.vacancy.id)

    async def test_worker_reads_saved_embedding_without_downloading_file(self):
        for path, repository in zip(
            self.embedding_paths, (self.resume_repository, self.vacancy_repository),
        ):
            for embedding in ([0.1, -0.2], [], None):
                with self.subTest(path=path, embedding=embedding):
                    repository.get_by_id.return_value = SimpleNamespace(
                        user_id=self.user_id, embedding=embedding,
                    )
                    status, _, body = await self.request(path)

                    self.assertEqual(status, 200)
                    self.assertEqual(json.loads(body), embedding)
        self.storage.get_bytes.assert_not_awaited()

    async def test_worker_updates_embedding_without_user_jwt(self):
        status, _, _ = await self.request(
            self.paths[1], method="PATCH", payload={"embedding": [0.1, -0.2]},
        )
        self.assertEqual(status, 200)
        self.vacancy_repository.set_embedding.assert_awaited_once()
        vacancy_id, data = self.vacancy_repository.set_embedding.call_args.args
        self.assertEqual(vacancy_id, self.vacancy.id)
        self.assertEqual(data.embedding, [0.1, -0.2])

    async def test_patch_rejects_invalid_worker_token(self):
        for token in (None, "wrong-token"):
            with self.subTest(token=token):
                status, _, _ = await self.request(
                    self.paths[1], token=token, method="PATCH", payload={"embedding": [0.1]},
                )
                self.assertEqual(status, 401)
        self.vacancy_repository.get_by_id.assert_not_awaited()
        self.vacancy_repository.set_embedding.assert_not_awaited()

    async def test_worker_updates_resume_embedding_without_user_jwt(self):
        status, _, body = await self.request(
            self.paths[0], method="PATCH", payload={"embedding": [0.1, -0.2]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["embedding"], [0.1, -0.2])
        self.resume_repository.set_embedding.assert_awaited_once()
        resume_id, data = self.resume_repository.set_embedding.call_args.args
        self.assertEqual(resume_id, self.resume.id)
        self.assertEqual(data.embedding, [0.1, -0.2])
        self.storage.get_bytes.assert_not_awaited()

    async def test_resume_patch_rejects_invalid_worker_token(self):
        for token in (None, "wrong-token"):
            with self.subTest(token=token):
                status, _, _ = await self.request(
                    self.paths[0], token=token, method="PATCH", payload={"embedding": [0.1]},
                )
                self.assertEqual(status, 401)
        self.resume_repository.get_by_id.assert_not_awaited()
        self.resume_repository.set_embedding.assert_not_awaited()

    async def test_resume_patch_wrong_owner_or_missing_resume_does_not_update(self):
        for resume in (self.resume, None):
            with self.subTest(resume=resume):
                self.resume_repository.get_by_id.return_value = resume
                status, _, _ = await self.request(
                    self.paths[0], query=f"user_id={uuid.uuid4()}",
                    method="PATCH", payload={"embedding": [0.1]},
                )
                self.assertEqual(status, 404)
        self.resume_repository.set_embedding.assert_not_awaited()

    async def test_resume_removed_before_update_returns_404(self):
        self.resume_repository.set_embedding.return_value = None
        status, _, _ = await self.request(
            self.paths[0], method="PATCH", payload={"embedding": [0.1]},
        )
        self.assertEqual(status, 404)

    async def test_patch_wrong_owner_or_missing_vacancy_does_not_update(self):
        for vacancy in (self.vacancy, None):
            with self.subTest(vacancy=vacancy):
                self.vacancy_repository.get_by_id.return_value = vacancy
                status, _, _ = await self.request(
                    self.paths[1], query=f"user_id={uuid.uuid4()}",
                    method="PATCH", payload={"embedding": [0.1]},
                )
                self.assertEqual(status, 404)
        self.vacancy_repository.set_embedding.assert_not_awaited()

    async def test_patch_vacancy_removed_before_update_returns_404(self):
        self.vacancy_repository.set_embedding.return_value = None
        status, _, _ = await self.request(
            self.paths[1], method="PATCH", payload={"embedding": [0.1]},
        )
        self.assertEqual(status, 404)

    async def test_wrong_owner_hidden(self):
        for path in self.paths + self.embedding_paths:
            with self.subTest(path=path):
                status, _, _ = await self.request(path, query=f"user_id={uuid.uuid4()}")
                self.assertEqual(status, 404)
        self.storage.get_bytes.assert_not_awaited()

    async def test_missing_resources_hidden(self):
        self.resume_repository.get_by_id.return_value = None
        self.vacancy_repository.get_by_id.return_value = None
        for path in self.paths + self.embedding_paths:
            with self.subTest(path=path):
                status, _, _ = await self.request(path)
                self.assertEqual(status, 404)
        self.storage.get_bytes.assert_not_awaited()

    async def test_user_id_required_and_validated(self):
        for path in self.paths + self.embedding_paths:
            for query in ("", "user_id=invalid"):
                with self.subTest(path=path, query=query):
                    status, _, _ = await self.request(path, query=query)
                    self.assertEqual(status, 422)
        self.resume_repository.get_by_id.assert_not_awaited()
        self.vacancy_repository.get_by_id.assert_not_awaited()

    async def test_worker_token_does_not_authorize_public_routes(self):
        for path in self.paths:
            with self.subTest(path=path):
                status, _, _ = await self.request(path.removeprefix("/internal"))
                self.assertEqual(status, 401)
        self.resume_repository.get_by_id.assert_not_awaited()
        self.vacancy_repository.get_by_id.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
