import json
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI

from app.api.users import api_v1_router
from app.core.security.deps import get_token_provider
from app.core.security.token import JWTTokenProvider
from app.schemas.users import UserResponseSchema
from app.services.users import UserService
from app.use_cases.users import get_user_service


class UserAccessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_id = uuid.uuid4()
        self.user = UserResponseSchema(
            user_id=uuid.uuid4(), username="other-user", is_active=True, is_staff=False,
        )
        self.payload = {
            "user_id": str(self.user_id), "username": "test-user", "is_staff": False,
        }
        self.secret = "auth-route-tests-only-secret-key-32-bytes"
        self.tokens = JWTTokenProvider(secret_key=self.secret)
        self.repository = SimpleNamespace(
            users=AsyncMock(return_value=[self.user]),
            get_user_by_id=AsyncMock(return_value=self.user),
        )
        self.service = UserService(self.repository)
        self.service.list_users = AsyncMock(wraps=self.service.list_users)
        self.service.detail = AsyncMock(wraps=self.service.detail)
        self.app = FastAPI()
        self.app.include_router(api_v1_router)
        self.app.dependency_overrides[get_user_service] = lambda: self.service
        self.app.dependency_overrides[get_token_provider] = lambda: self.tokens
        self.paths = ("/auth/users", f"/auth/users/{self.user.user_id}")

    async def request(self, path, token=None, query="", headers=None, payload=None):
        messages = []
        request_headers = [] if headers is None else list(headers)
        if token is not None:
            request_headers.append((b"authorization", f"Bearer {token}".encode()))
        if payload is not None:
            request_headers.append((b"content-type", b"application/json"))

        async def receive():
            body = b"" if payload is None else json.dumps(payload).encode()
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        await self.app({
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": "GET", "scheme": "http", "path": path, "root_path": "",
            "query_string": query.encode(), "headers": request_headers,
            "server": ("test", 80), "client": ("test", 1234),
        }, receive, send)
        response = next(message for message in messages if message["type"] == "http.response.start")
        body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
        return response["status"], dict(response["headers"]), json.loads(body)

    def assert_no_user_reads(self):
        self.service.list_users.assert_not_called()
        self.service.detail.assert_not_called()
        self.repository.users.assert_not_called()
        self.repository.get_user_by_id.assert_not_called()

    async def test_anonymous_requests_are_rejected(self):
        for path in (*self.paths, "/auth/me"):
            with self.subTest(path=path):
                status, headers, _ = await self.request(path)
                self.assertEqual(status, 401)
                self.assertEqual(headers[b"www-authenticate"], b"Bearer")
        self.assert_no_user_reads()

    async def test_invalid_tokens_are_rejected(self):
        staff_payload = {**self.payload, "is_staff": True}
        expired_tokens = JWTTokenProvider(secret_key=self.secret, access_expire_min=-1)
        other_tokens = JWTTokenProvider(secret_key="another-test-only-secret-key-32-bytes")
        tokens = {
            "malformed": "invalid-token",
            "expired": expired_tokens.create_access_token(staff_payload),
            "wrong-signature": other_tokens.create_access_token(staff_payload),
            "refresh": self.tokens.create_refresh_token(self.user_id),
        }
        for path in (*self.paths, "/auth/me"):
            for name, token in tokens.items():
                with self.subTest(path=path, token=name):
                    status, headers, _ = await self.request(path, token=token)
                    self.assertEqual(status, 401)
                    self.assertEqual(headers[b"www-authenticate"], b"Bearer")
        self.assert_no_user_reads()

    async def test_regular_user_cannot_read_users(self):
        token = self.tokens.create_access_token(self.payload)
        for path in self.paths:
            with self.subTest(path=path):
                status, _, body = await self.request(path, token=token)
                self.assertEqual(status, 403)
                self.assertEqual(body, {"detail": "Staff access required"})
        self.assert_no_user_reads()

    async def test_regular_user_cannot_read_own_user_route(self):
        token = self.tokens.create_access_token(self.payload)
        status, _, _ = await self.request(f"/auth/users/{self.user_id}", token=token)
        self.assertEqual(status, 403)
        self.assert_no_user_reads()

    async def test_client_supplied_role_cannot_grant_access(self):
        token = self.tokens.create_access_token(self.payload)
        for path in self.paths:
            with self.subTest(path=path):
                status, _, _ = await self.request(
                    path, token=token, query="is_staff=true&role=staff",
                    headers=[(b"is_staff", b"true"), (b"x-role", b"staff")],
                    payload={"is_staff": True, "role": "staff"},
                )
                self.assertEqual(status, 403)
        self.assert_no_user_reads()

    async def test_staff_can_list_users(self):
        token = self.tokens.create_access_token({**self.payload, "is_staff": True})
        status, _, body = await self.request(self.paths[0], token=token)
        self.assertEqual(status, 200)
        self.assertEqual(body, [self.user.model_dump(mode="json")])
        self.service.list_users.assert_awaited_once_with()
        self.repository.users.assert_awaited_once_with()
        self.service.detail.assert_not_called()

    async def test_staff_can_read_user(self):
        token = self.tokens.create_access_token({**self.payload, "is_staff": True})
        status, _, body = await self.request(self.paths[1], token=token)
        self.assertEqual(status, 200)
        self.assertEqual(body, self.user.model_dump(mode="json"))
        self.service.detail.assert_awaited_once_with(id=self.user.user_id)
        self.repository.get_user_by_id.assert_awaited_once_with(self.user.user_id)
        self.service.list_users.assert_not_called()

    async def test_staff_gets_not_found_for_missing_user(self):
        self.repository.get_user_by_id.return_value = None
        token = self.tokens.create_access_token({**self.payload, "is_staff": True})
        status, _, body = await self.request(self.paths[1], token=token)
        self.assertEqual(status, 404)
        self.assertEqual(body, {"detail": "User not found"})
        self.service.detail.assert_awaited_once_with(id=self.user.user_id)
        self.repository.get_user_by_id.assert_awaited_once_with(self.user.user_id)
        self.service.list_users.assert_not_called()

    async def test_authenticated_users_can_read_own_profile(self):
        for is_staff in (False, True):
            with self.subTest(is_staff=is_staff):
                payload = {**self.payload, "is_staff": is_staff}
                token = self.tokens.create_access_token(payload)
                status, _, body = await self.request("/auth/me", token=token)
                self.assertEqual(status, 200)
                self.assertEqual(body, payload)
        self.assert_no_user_reads()


if __name__ == "__main__":
    unittest.main()
