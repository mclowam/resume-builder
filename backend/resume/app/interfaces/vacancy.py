import uuid
from typing import Protocol

from app.schemas.vacancy import VacancyCreateSchema, VacancyResponseSchema


class IVacancy(Protocol):
    async def add(self, data: VacancyCreateSchema):
        pass

    async def get_by_id(self, vacancy_id: uuid.UUID) -> VacancyResponseSchema:
        pass

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[VacancyResponseSchema]:
        pass
