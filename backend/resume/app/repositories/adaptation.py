import uuid

from sqlalchemy import select, update

from app.db.session import SessionDep
from app.models.adaptation import Adaptation
from app.models.outbox import OutboxEvent
from app.schemas.adaptation import AdaptationCreateSchema, AdaptationResponseSchema, AdaptationFinishSchema
from app.schemas.event import AdaptationRequestedEvent


class AdaptationRepository:
    def __init__(self, session: SessionDep):
        self._session = session

    async def add(self, data: AdaptationCreateSchema, user_id: uuid.UUID) -> AdaptationResponseSchema:
        adaptation = Adaptation(id=uuid.uuid4(), user_id=user_id, resume_id=data.resume_id, vacancy_id=data.vacancy_id)
        self._session.add(adaptation)
        event = AdaptationRequestedEvent(adaptation_id=adaptation.id, user_id=user_id)
        self._session.add(OutboxEvent(payload=event.model_dump(mode="json")))
        await self._session.flush()
        await self._session.refresh(adaptation)
        await self._session.commit()

        return AdaptationResponseSchema.model_validate(adaptation)

    async def claim(self, adaptation_id: uuid.UUID, user_id: uuid.UUID) -> AdaptationResponseSchema | None:
        query = (
            update(Adaptation)
            .where(Adaptation.id == adaptation_id, Adaptation.user_id == user_id, Adaptation.status == "pending")
            .values(status="running")
            .returning(Adaptation)
        )
        result = await self._session.execute(query)
        adaptation = result.scalar_one_or_none()
        await self._session.commit()
        return None if adaptation is None else AdaptationResponseSchema.model_validate(adaptation)

    async def finish(
            self, adaptation_id: uuid.UUID, user_id: uuid.UUID, data: AdaptationFinishSchema,
    ) -> AdaptationResponseSchema | None:
        query = (
            update(Adaptation)
            .where(Adaptation.id == adaptation_id, Adaptation.user_id == user_id, Adaptation.status == "running")
            .values(**data.model_dump(mode="json"))
            .returning(Adaptation)
        )
        result = await self._session.execute(query)
        adaptation = result.scalar_one_or_none()
        await self._session.commit()
        return None if adaptation is None else AdaptationResponseSchema.model_validate(adaptation)

    async def get_by_id(self, adaptation_id: uuid.UUID, user_id: uuid.UUID) -> AdaptationResponseSchema | None:
        query = select(Adaptation).where(Adaptation.id == adaptation_id, Adaptation.user_id == user_id)
        result = await self._session.execute(query)
        adaptation = result.scalar_one_or_none()
        if adaptation is None:
            return None

        return AdaptationResponseSchema.model_validate(adaptation)
