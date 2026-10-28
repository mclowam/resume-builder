import uuid
from fastapi import HTTPException

from app.interfaces.vacancy import IVacancy
from app.schemas.vacancy import VacancyCreateSchema, VacancyResponseSchema, VacancySetEmbeddingSchema


class VacancyService:
    def __init__(
            self,
            vacancy_repository: IVacancy,
    ):
        self._vacancy_repo = vacancy_repository

    async def create_vacancy(self, data: VacancyCreateSchema, user_id: uuid.UUID) -> VacancyResponseSchema:
        vacancy = await self._vacancy_repo.add(data, user_id)

        return VacancyResponseSchema(
            id=vacancy.id,
            user_id=vacancy.user_id,
            text=vacancy.text,
            embedding=vacancy.embedding
        )

    async def get_by_id(self, vacancy_id: uuid.UUID) -> VacancyResponseSchema:
        vacancy = await self._vacancy_repo.get_by_id(vacancy_id)

        if vacancy is None:
            raise HTTPException(detail="Vacancy not found", status_code=404)

        return vacancy

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[VacancyResponseSchema]:
        vacancies = await self._vacancy_repo.get_by_user_id(user_id)

        return vacancies

    async def set_embedding(self, vacancy_id: uuid.UUID, data: VacancySetEmbeddingSchema):
        vacancy = await self._vacancy_repo.set_embedding(vacancy_id, data)

        if vacancy is None:
            raise HTTPException(detail="Vacancy not found", status_code=404)

        return vacancy
