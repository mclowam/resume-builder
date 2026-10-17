import math

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
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Document text must not be empty")
        response = await self._client.post(
            "embeddings",
            json={"model": self.model, "input": text, "encoding_format": "float"},
        )
        response.raise_for_status()
        try:
            embedding = response.json()["data"][0]["embedding"]
            if not isinstance(embedding, list) or not embedding:
                raise ValueError
            if any(type(value) not in (int, float) or not math.isfinite(value) for value in embedding):
                raise ValueError
            return [float(value) for value in embedding]
        except (KeyError, IndexError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Invalid embedding response") from exc

    async def close(self) -> None:
        await self._client.aclose()
