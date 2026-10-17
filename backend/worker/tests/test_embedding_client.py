import json
import unittest
from unittest.mock import patch

import httpx

from app.clients.embedding import EmbeddingHttpClient


class EmbeddingHttpClientTests(unittest.IsolatedAsyncioTestCase):
    async def create_client(self, handler, base_url="https://api.openai.com/v1"):
        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(base_url=base_url, transport=transport)
        with patch("app.clients.embedding.httpx.AsyncClient", return_value=http_client) as factory:
            client = EmbeddingHttpClient(base_url, "test-api-key", "text-embedding-3-small")
        http_client.headers.update(factory.call_args.kwargs["headers"])
        self.addAsyncCleanup(client.close)
        return client

    async def test_sends_full_text_and_returns_vector(self):
        text = "  Разработчик\nPython\nОпыт работы  "
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"data": [{"embedding": [0.12, -0.34, 1.0]}]})

        for base_url in ("https://api.openai.com/v1", "https://api.openai.com/v1/"):
            with self.subTest(base_url=base_url):
                client = await self.create_client(handler, base_url)

                embedding = await client.embed(text)

                request = requests[-1]
                self.assertEqual(request.method, "POST")
                self.assertEqual(str(request.url), "https://api.openai.com/v1/embeddings")
                self.assertEqual(request.headers["Authorization"], "Bearer test-api-key")
                self.assertEqual(json.loads(request.content), {
                    "model": "text-embedding-3-small", "input": text, "encoding_format": "float",
                })
                self.assertEqual(embedding, [0.12, -0.34, 1.0])
                self.assertTrue(all(isinstance(value, float) for value in embedding))
                await client.close()
                self.assertTrue(client._client.is_closed)

    async def test_propagates_api_errors_without_retry(self):
        for status in (400, 401, 429, 500):
            with self.subTest(status=status):
                requests = []

                def handler(request):
                    requests.append(request)
                    return httpx.Response(status, json={"error": {"message": "Failed"}})

                client = await self.create_client(handler)
                with self.assertRaises(httpx.HTTPStatusError) as raised:
                    await client.embed("Full text")

                self.assertEqual(raised.exception.response.status_code, status)
                self.assertEqual(len(requests), 1)

    async def test_propagates_timeout(self):
        def handler(request):
            raise httpx.ReadTimeout("Timed out", request=request)

        client = await self.create_client(handler)
        with self.assertRaises(httpx.ReadTimeout):
            await client.embed("Full text")

    async def test_rejects_invalid_json(self):
        client = await self.create_client(lambda request: httpx.Response(200, content="not json"))
        with self.assertRaises(json.JSONDecodeError):
            await client.embed("Full text")


if __name__ == "__main__":
    unittest.main()
