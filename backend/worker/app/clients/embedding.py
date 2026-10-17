import httpx

from app.core.core import settings


class EmbeddingHttpClient:
    def __init__(self, base_url: str, api_key: str | None, model: str):
        if not api_key or not api_key.strip():
            raise ValueError("OPENAI_API_KEY must not be empty")
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=settings.HTTP_TIME_OUT,
            headers={"Authorization": f"Bearer {api_key.strip()}"},
        )

    async def embed(self, text: str) -> list[float]:
        response = await self._client.post(
            "embeddings",
            json={"model": self.model, "input": text, "encoding_format": "float"},
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

    async def close(self) -> None:
        await self._client.aclose()
