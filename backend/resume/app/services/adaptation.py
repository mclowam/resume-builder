import uuid

from fastapi import HTTPException

from app.interfaces.adaptation import IAdaptation
from app.interfaces.resume import IResume
from app.interfaces.vacancy import IVacancy
from app.schemas.adaptation import AdaptationCreateSchema, AdaptationResponseSchema, AdaptationFinishSchema


class AdaptationService:
    def __init__(
            self,
            adaptation_repository: IAdaptation,
            resume_repository: IResume,
            vacancy_repository: IVacancy,
    ):
        self._adaptation_repo = adaptation_repository
        self._resume_repo = resume_repository
        self._vacancy_repo = vacancy_repository

    async def create_adaptation(self, data: AdaptationCreateSchema, user_id: uuid.UUID) -> AdaptationResponseSchema:
        resume = await self._resume_repo.get_by_id(data.resume_id)
        if resume is None or resume.user_id != user_id:
            raise HTTPException(status_code=404, detail="Resume not found")

        vacancy = await self._vacancy_repo.get_by_id(data.vacancy_id)
        if vacancy is None or vacancy.user_id != user_id:
            raise HTTPException(status_code=404, detail="Vacancy not found")

        return await self._adaptation_repo.add(data, user_id)

    async def get_by_id(self, adaptation_id: uuid.UUID, user_id: uuid.UUID) -> AdaptationResponseSchema:
        adaptation = await self._adaptation_repo.get_by_id(adaptation_id, user_id)
        if adaptation is None:
            raise HTTPException(status_code=404, detail="Adaptation not found")

        return adaptation

    async def claim(self, adaptation_id: uuid.UUID, user_id: uuid.UUID) -> AdaptationResponseSchema | None:
        await self.get_by_id(adaptation_id, user_id)
        return await self._adaptation_repo.claim(adaptation_id, user_id)

    async def finish(
            self, adaptation_id: uuid.UUID, user_id: uuid.UUID, data: AdaptationFinishSchema,
    ) -> AdaptationResponseSchema:
        await self.get_by_id(adaptation_id, user_id)
        adaptation = await self._adaptation_repo.finish(adaptation_id, user_id, data)
        if adaptation is None:
            raise HTTPException(status_code=409, detail="Adaptation is not running")
        return adaptation
