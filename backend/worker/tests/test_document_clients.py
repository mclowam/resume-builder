import json
import uuid
from unittest.mock import patch

import httpx
import pytest

from app.clients.resume import ResumeHttpClient
from app.clients.vacancy import VacancyHttpClient
from app.core.core import settings
from app.schemas.embedding import PatchEmbeddingSchema


class TestDocumentClient:
    @pytest.fixture(autouse=True)
    def setup(self, cleanup):
        self.cleanup = cleanup
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
        self.cleanup.push_async_callback(client.close)
        return client

    async def test_patches_embedding_for_owner(self, subtests):
        for client_type, resource in (
            (ResumeHttpClient, "resumes"), (VacancyHttpClient, "vacancies"),
        ):
            with subtests.test(resource=resource):
                requests = []
                result = {"id": str(self.resource_id), "embedding": [0.1, -0.2]}

                def handler(request):
                    requests.append(request)
                    return httpx.Response(200, json=result)

                client = self.create_client(client_type, handler)
                response = await client.set_embedding(self.resource_id, self.user_id, self.data)

                assert response == result
                assert len(requests) == 1
                request = requests[0]
                assert request.method == "PATCH"
                assert str(request.url) == f"http://resume:8000/internal/{resource}/{self.resource_id}?user_id={self.user_id}"
                assert request.headers["X-Worker-Token"] == "test-worker-token"
                assert json.loads(request.content) == {"embedding": [0.1, -0.2]}

    async def test_gets_embedding_for_owner(self, subtests):
        for client_type, resource in (
            (ResumeHttpClient, "resumes"), (VacancyHttpClient, "vacancies"),
        ):
            for embedding in (None, [], [0.1, -0.2]):
                with subtests.test(resource=resource, embedding=embedding):
                    requests = []

                    def handler(request):
                        requests.append(request)
                        return httpx.Response(200, content=json.dumps(embedding))

                    client = self.create_client(client_type, handler)

                    assert await client.get_embedding(self.resource_id, self.user_id) == embedding
                    assert len(requests) == 1
                    assert requests[0].method == "GET"
                    assert str(requests[0].url) == f"http://resume:8000/internal/{resource}/{self.resource_id}/embedding?user_id={self.user_id}"
                    assert requests[0].headers["X-Worker-Token"] == "test-worker-token"

    async def test_propagates_embedding_lookup_errors(self, subtests):
        for client_type in (ResumeHttpClient, VacancyHttpClient):
            for status in (401, 404, 500):
                with subtests.test(client=client_type.__name__, status=status):
                    client = self.create_client(
                        client_type, lambda request: httpx.Response(status, text="Failed"),
                    )

                    with pytest.raises(httpx.HTTPStatusError):
                        await client.get_embedding(self.resource_id, self.user_id)

    async def test_propagates_patch_status_errors(self, subtests):
        for client_type in (ResumeHttpClient, VacancyHttpClient):
            for status in (401, 404, 500):
                with subtests.test(client=client_type.__name__, status=status):
                    client = self.create_client(
                        client_type, lambda request: httpx.Response(status, text="Failed"),
                    )

                    with pytest.raises(httpx.HTTPStatusError) as raised:
                        await client.set_embedding(self.resource_id, self.user_id, self.data)

                    assert raised.value.response.status_code == status

    async def test_propagates_patch_timeout(self, subtests):
        def handler(request):
            raise httpx.ReadTimeout("Timed out", request=request)

        for client_type in (ResumeHttpClient, VacancyHttpClient):
            with subtests.test(client=client_type.__name__):
                client = self.create_client(client_type, handler)

                with pytest.raises(httpx.ReadTimeout):
                    await client.set_embedding(self.resource_id, self.user_id, self.data)
