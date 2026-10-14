import uuid
from sqlalchemy import select

from app.db.session import SessionDep
from app.models.outbox import OutboxEvent
from app.models.resume import Resume
from app.schemas.event import ResumeUploadedEvent
from app.schemas.resume import ResumeCreateSchema, ResumeResponseSchema


class ResumeRepository:
    def __init__(self, session: SessionDep):
        self._session = session

    async def add(self, data: ResumeCreateSchema, user_id: uuid.UUID):
        resume = Resume(
            id=uuid.uuid4(),
            user_id=user_id,
            file_url=data.file_url,
            embedding=data.embedding
        )
        self._session.add(resume)
        event = ResumeUploadedEvent(resume_id=resume.id, user_id=resume.user_id)
        self._session.add(OutboxEvent(payload=event.model_dump(mode="json")))
        await self._session.flush()
        await self._session.refresh(resume)
        await self._session.commit()

        return resume

    async def get_by_id(self, resume_id: uuid.UUID) -> ResumeResponseSchema | None:
        query = select(Resume).where(Resume.id == resume_id)
        result = await self._session.execute(query)

        resume = result.scalar_one_or_none()
        if resume is None:
            return None

        return ResumeResponseSchema(
            id=resume.id,
            user_id=resume.user_id,
            file_url=resume.file_url,
            embedding=resume.embedding,
            created_at=resume.created_at
        )

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[ResumeResponseSchema]:
        query = select(Resume).where(Resume.user_id == user_id)
        result = await self._session.execute(query)

        return [
            ResumeResponseSchema(
                id=resume.id,
                user_id=resume.user_id,
                file_url=resume.file_url,
                embedding=resume.embedding,
                created_at=resume.created_at
            )
            for resume in result.scalars().all()
        ]
