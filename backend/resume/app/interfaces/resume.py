import uuid
from typing import Protocol

from app.schemas.resume import ResumeCreateSchema, ResumeResponseSchema


class IResume(Protocol):
    async def add(self, data: ResumeCreateSchema, user_id: uuid.UUID):
        pass

    async def get_by_id(self, resume_id: uuid.UUID) -> ResumeResponseSchema | None:
        pass

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[ResumeResponseSchema]:
        pass
