import uuid
from typing import Protocol

from app.schemas.adaptation import AdaptationCreateSchema, AdaptationResponseSchema, AdaptationFinishSchema


class IAdaptation(Protocol):
    async def claim(self, adaptation_id: uuid.UUID, user_id: uuid.UUID) -> AdaptationResponseSchema | None:
        pass

    async def finish(
            self, adaptation_id: uuid.UUID, user_id: uuid.UUID, data: AdaptationFinishSchema,
    ) -> AdaptationResponseSchema | None:
        pass

    async def add(self, data: AdaptationCreateSchema, user_id: uuid.UUID) -> AdaptationResponseSchema:
        pass

    async def get_by_id(self, adaptation_id: uuid.UUID, user_id: uuid.UUID) -> AdaptationResponseSchema | None:
        pass
