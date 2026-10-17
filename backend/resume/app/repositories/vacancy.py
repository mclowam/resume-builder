import uuid
from sqlalchemy import select

from app.db.session import SessionDep
from app.models.outbox import OutboxEvent
from app.models.vacancy import Vacancy
from app.schemas.event import VacancyUploadedEvent
from app.schemas.vacancy import VacancyCreateSchema, VacancyResponseSchema, VacancySetEmbeddingSchema


class VacancyRepository:
    def __init__(self, session: SessionDep):
        self._session = session

    async def add(self, data: VacancyCreateSchema, user_id: uuid.UUID):
        vacancy = Vacancy(
            id=uuid.uuid4(),
            user_id=user_id,
            text=data.text
        )
        self._session.add(vacancy)
        event = VacancyUploadedEvent(vacancy_id=vacancy.id, user_id=vacancy.user_id)
        self._session.add(OutboxEvent(payload=event.model_dump(mode="json")))
        await self._session.flush()
        await self._session.refresh(vacancy)
        await self._session.commit()

        return vacancy

    async def get_by_id(self, vacancy_id: uuid.UUID) -> VacancyResponseSchema | None:
        query = select(Vacancy).where(Vacancy.id == vacancy_id)
        result = await self._session.execute(query)

        vacancy = result.scalar_one_or_none()
        if vacancy is None:
            return None

        return VacancyResponseSchema(
            id=vacancy.id,
            user_id=vacancy.user_id,
            text=vacancy.text
        )

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[VacancyResponseSchema]:
        query = select(Vacancy).where(Vacancy.user_id == user_id)
        result = await self._session.execute(query)

        return [
            VacancyResponseSchema(id=vacancy.id, user_id=vacancy.user_id, text=vacancy.text)
            for vacancy in result.scalars().all()
        ]

    async def set_embedding(self, vacancy_id: uuid.UUID, data: VacancySetEmbeddingSchema):
        query = select(Vacancy).where(Vacancy.id == vacancy_id)
        result = await self._session.execute(query)

        vacancy = result.scalar_one_or_none()
        if vacancy is None:
            return None

        vacancy.embedding = data.embedding
        await self._session.commit()

        return vacancy
