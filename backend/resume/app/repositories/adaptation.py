import uuid

from sqlalchemy import select

from app.db.session import SessionDep
from app.models.adaptation import Adaptation
from app.schemas.adaptation import AdaptationCreateSchema, AdaptationResponseSchema


class AdaptationRepository:
    def __init__(self, session: SessionDep):
        self._session = session

    async def add(self, data: AdaptationCreateSchema, user_id: uuid.UUID) -> AdaptationResponseSchema:
        adaptation = Adaptation(user_id=user_id, resume_id=data.resume_id, vacancy_id=data.vacancy_id)
        self._session.add(adaptation)
        await self._session.flush()
        await self._session.refresh(adaptation)
        await self._session.commit()

        return AdaptationResponseSchema.model_validate(adaptation)

    async def get_by_id(self, adaptation_id: uuid.UUID, user_id: uuid.UUID) -> AdaptationResponseSchema | None:
        query = select(Adaptation).where(Adaptation.id == adaptation_id, Adaptation.user_id == user_id)
        result = await self._session.execute(query)
        adaptation = result.scalar_one_or_none()
        if adaptation is None:
            return None

        return AdaptationResponseSchema.model_validate(adaptation)
