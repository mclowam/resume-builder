import json
import unittest
import uuid
from unittest.mock import patch

import httpx

from app.clients.resume import ResumeHttpClient
from app.clients.vacancy import VacancyHttpClient
from app.core.core import settings
from app.schemas.embedding import PatchEmbeddingSchema


class DocumentClientTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.resource_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.data = PatchEmbeddingSchema(embedding=[0.1, -0.2])

    def create_client(self, client_type, handler):
        async_client = httpx.AsyncClient
        transport = httpx.MockTransport(handler)
        with (
            patch.object(settings, "WORKER_API_TOKEN", "test-worker-token"),
            patch("httpx.AsyncClient", side_effect=lambda **kwargs: async_client(transport=transport, **kwargs)),
        ):
            client = client_type("http://resume:8000")
        self.addAsyncCleanup(client.close)
        return client

    async def test_patches_embedding_for_owner(self):
        for client_type, resource in (
            (ResumeHttpClient, "resumes"), (VacancyHttpClient, "vacancies"),
        ):
            with self.subTest(resource=resource):
                requests = []
                result = {"id": str(self.resource_id), "embedding": [0.1, -0.2]}

                def handler(request):
                    requests.append(request)
                    return httpx.Response(200, json=result)

                client = self.create_client(client_type, handler)
                response = await client.set_embedding(self.resource_id, self.user_id, self.data)

                self.assertEqual(response, result)
                self.assertEqual(len(requests), 1)
                request = requests[0]
                self.assertEqual(request.method, "PATCH")
                self.assertEqual(
                    str(request.url),
                    f"http://resume:8000/internal/{resource}/{self.resource_id}?user_id={self.user_id}",
                )
                self.assertEqual(request.headers["X-Worker-Token"], "test-worker-token")
                self.assertEqual(json.loads(request.content), {"embedding": [0.1, -0.2]})

    async def test_propagates_patch_status_errors(self):
        for client_type in (ResumeHttpClient, VacancyHttpClient):
            for status in (401, 404, 500):
                with self.subTest(client=client_type.__name__, status=status):
                    client = self.create_client(
                        client_type, lambda request: httpx.Response(status, text="Failed"),
                    )

                    with self.assertRaises(httpx.HTTPStatusError) as raised:
                        await client.set_embedding(self.resource_id, self.user_id, self.data)

                    self.assertEqual(raised.exception.response.status_code, status)

    async def test_propagates_patch_timeout(self):
        def handler(request):
            raise httpx.ReadTimeout("Timed out", request=request)

        for client_type in (ResumeHttpClient, VacancyHttpClient):
            with self.subTest(client=client_type.__name__):
                client = self.create_client(client_type, handler)

                with self.assertRaises(httpx.ReadTimeout):
                    await client.set_embedding(self.resource_id, self.user_id, self.data)


if __name__ == "__main__":
    unittest.main()
