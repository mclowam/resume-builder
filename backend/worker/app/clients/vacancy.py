import uuid

import httpx

from app.core.core import settings


class VacancyHttpClient:
    def __init__(self, base_url: settings.RESUME_API_URL):
        self._client = httpx.Client(base_url=base_url, timeout=settings.HTTP_TIMEOUT)

    async def get_vacancy(self, vacancy_id: uuid.UUID):
        response = self._client.get(f"vacancies/{vacancy_id}")
        response.raise_for_status()
        return response.json()

