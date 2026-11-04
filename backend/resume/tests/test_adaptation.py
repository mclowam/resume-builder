import json
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI

from app.api.adaptation import api_v1_router
from app.core.security.deps import get_current_user
from app.schemas.users import UserPayload
from app.services.adaptation import AdaptationService
from app.use_cases.adaptation import get_adaptation_service


class AdaptationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_id = uuid.uuid4()
        self.resume = SimpleNamespace(id=uuid.uuid4(), user_id=self.user_id)
        self.vacancy = SimpleNamespace(id=uuid.uuid4(), user_id=self.user_id)
        self.adaptation = SimpleNamespace(
            id=uuid.uuid4(), user_id=self.user_id, resume_id=self.resume.id,
            vacancy_id=self.vacancy.id, status="pending", result=None, error=None,
            created_at=datetime.now(timezone.utc),
        )
        self.repository = SimpleNamespace(
            add=AsyncMock(return_value=self.adaptation),
            get_by_id=AsyncMock(return_value=self.adaptation),
        )
        self.resume_repository = SimpleNamespace(get_by_id=AsyncMock(return_value=self.resume))
        self.vacancy_repository = SimpleNamespace(get_by_id=AsyncMock(return_value=self.vacancy))
        self.app = FastAPI()
        self.app.include_router(api_v1_router)
        self.app.dependency_overrides[get_current_user] = lambda: UserPayload(
            user_id=self.user_id, username="test", is_staff=False,
        )
        self.app.dependency_overrides[get_adaptation_service] = lambda: AdaptationService(
            self.repository, self.resume_repository, self.vacancy_repository,
        )
        self.payload = {"resume_id": str(self.resume.id), "vacancy_id": str(self.vacancy.id)}

    async def request(self, path="/adaptations", method="POST", payload=None):
        messages = []

        async def receive():
            return {"type": "http.request", "body": json.dumps(payload).encode(), "more_body": False}

        async def send(message):
            messages.append(message)

        await self.app({
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": method, "scheme": "http", "path": path, "root_path": "",
            "query_string": b"", "headers": [(b"content-type", b"application/json")],
            "server": ("test", 80), "client": ("test", 1234),
        }, receive, send)
        response = next(message for message in messages if message["type"] == "http.response.start")
        body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
        return response["status"], dict(response["headers"]), json.loads(body)

    async def test_creates_pending_adaptation_for_authenticated_owner(self):
        status, headers, body = await self.request(payload=self.payload)
        self.assertEqual(status, 201)
        self.assertEqual(headers[b"location"].decode(), f"/adaptations/{self.adaptation.id}")
        self.assertEqual(body["user_id"], str(self.user_id))
        self.assertEqual(body["status"], "pending")
        self.assertIsNone(body["result"])
        self.assertIsNone(body["error"])

    async def test_missing_or_foreign_sources_do_not_create_adaptation(self):
        for repository in (self.resume_repository, self.vacancy_repository):
            original = repository.get_by_id.return_value
            for source in (None, SimpleNamespace(user_id=uuid.uuid4())):
                with self.subTest(repository=repository, source=source):
                    repository.get_by_id.return_value = source
                    status, _, _ = await self.request(payload=self.payload)
                    self.assertEqual(status, 404)
            repository.get_by_id.return_value = original
        self.repository.add.assert_not_awaited()

    async def test_rejects_injected_fields_and_invalid_ids(self):
        for payload in (
            {**self.payload, "user_id": str(uuid.uuid4())},
            {**self.payload, "status": "done"},
            {**self.payload, "result": {"resume_text": "fake"}},
            {**self.payload, "resume_id": "invalid"},
            {"resume_id": self.payload["resume_id"]},
        ):
            with self.subTest(payload=payload):
                status, _, _ = await self.request(payload=payload)
                self.assertEqual(status, 422)
        self.repository.add.assert_not_awaited()

    async def test_reads_owned_result_including_rejected_review(self):
        self.adaptation.status = "done"
        self.adaptation.result = {
            "resume_text": "Python", "review": {"passed": False, "issues": ["Unsupported fact"]},
        }
        status, _, body = await self.request(f"/adaptations/{self.adaptation.id}", "GET")
        self.assertEqual(status, 200)
        self.assertEqual(body["result"], self.adaptation.result)
        self.repository.get_by_id.assert_awaited_once_with(self.adaptation.id, self.user_id)

    async def test_missing_adaptation_is_hidden(self):
        self.repository.get_by_id.return_value = None
        status, _, _ = await self.request(f"/adaptations/{uuid.uuid4()}", "GET")
        self.assertEqual(status, 404)

    async def test_routes_require_authentication(self):
        del self.app.dependency_overrides[get_current_user]
        for method, path in (("POST", "/adaptations"), ("GET", f"/adaptations/{self.adaptation.id}")):
            status, _, _ = await self.request(path, method, self.payload)
            self.assertEqual(status, 401)
        self.repository.add.assert_not_awaited()
        self.repository.get_by_id.assert_not_awaited()
