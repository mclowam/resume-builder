import uuid

import httpx

from app.core.core import settings
from app.schemas.embedding import PatchEmbeddingSchema


class VacancyHttpClient:
    def __init__(self, base_url: str):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=settings.HTTP_TIME_OUT,
            headers={"X-Worker-Token": settings.WORKER_API_TOKEN or ""},
        )

    async def get_vacancy(self, vacancy_id: uuid.UUID, user_id: uuid.UUID):
        response = await self._client.get(
            f"/internal/vacancies/{vacancy_id}",
            params={"user_id": str(user_id)},
        )
        response.raise_for_status()
        return response.json()

    async def set_embedding(self, vacancy_id: uuid.UUID, user_id: uuid.UUID, data: PatchEmbeddingSchema):
        response = await self._client.patch(
            f"/internal/vacancies/{vacancy_id}",
            params={"user_id": str(user_id)},
            json=data.model_dump(mode="json"),
        )
        response.raise_for_status()
        return response.json()

    async def get_embedding(self, vacancy_id: uuid.UUID, user_id: uuid.UUID) -> list[float] | None:
        response = await self._client.get(
            f"/internal/vacancies/{vacancy_id}/embedding",
            params={"user_id": str(user_id)},
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()

