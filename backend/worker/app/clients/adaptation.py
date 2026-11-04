import uuid

import httpx

from app.core.core import settings


class AdaptationHttpClient:
    def __init__(self, base_url: str):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=settings.HTTP_TIME_OUT,
            headers={"X-Worker-Token": settings.WORKER_API_TOKEN or ""},
        )

    async def claim(self, adaptation_id: uuid.UUID, user_id: uuid.UUID) -> dict | None:
        response = await self._client.post(
            f"/internal/adaptations/{adaptation_id}/claim", params={"user_id": str(user_id)},
        )
        response.raise_for_status()
        return response.json()

    async def save(self, adaptation_id: uuid.UUID, user_id: uuid.UUID, data: dict) -> None:
        response = await self._client.patch(
            f"/internal/adaptations/{adaptation_id}", params={"user_id": str(user_id)}, json=data,
        )
        response.raise_for_status()

    async def close(self) -> None:
        await self._client.aclose()
