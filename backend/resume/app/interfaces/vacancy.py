import uuid
from typing import Protocol

from app.schemas.vacancy import VacancyCreateSchema, VacancyResponseSchema, VacancySetEmbeddingSchema


class IVacancy(Protocol):
    async def add(self, data: VacancyCreateSchema, user_id: uuid.UUID):
        pass

    async def get_by_id(self, vacancy_id: uuid.UUID) -> VacancyResponseSchema | None:
        pass

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[VacancyResponseSchema]:
        pass

    async def set_embedding(self, vacancy_id: uuid.UUID, data: VacancySetEmbeddingSchema):
        pass