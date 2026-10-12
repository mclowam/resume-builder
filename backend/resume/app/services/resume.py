import uuid
from fastapi import HTTPException

from app.interfaces.event_publisher import IEventPublisher
from app.interfaces.resume import IResume
from app.schemas.resume import ResumeCreateSchema, ResumeResponseSchema


class ResumeService:
    def __init__(
            self,
            resume_repository: IResume,
            event_publisher: IEventPublisher,
    ):
        self._resume_repo = resume_repository
        self._event_publisher = event_publisher

    async def create_resume(self, data: ResumeCreateSchema, user_id: uuid.UUID) -> ResumeResponseSchema:
        resume = await self._resume_repo.add(data, user_id)

        return ResumeResponseSchema(
            id=resume.id,
            user_id=resume.user_id,
            image_url=resume.image_url,
            embedding=resume.embedding,
            created_at=resume.created_at
        )

    async def get_by_id(self, resume_id: uuid.UUID) -> ResumeResponseSchema:
        resume = await self._resume_repo.get_by_id(resume_id)

        if resume is None:
            raise HTTPException(detail="Resume not found", status_code=404)

        return resume

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[ResumeResponseSchema]:
        resumes = await self._resume_repo.get_by_user_id(user_id)

        return resumes
