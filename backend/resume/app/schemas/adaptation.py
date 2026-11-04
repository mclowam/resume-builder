import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AdaptationCreateSchema(BaseModel, extra="forbid"):
    resume_id: uuid.UUID
    vacancy_id: uuid.UUID


class AdaptationReviewSchema(BaseModel):
    passed: bool
    issues: list[str]


class AdaptationResultSchema(BaseModel):
    resume_text: str = Field(pattern=r"\S")
    review: AdaptationReviewSchema


class AdaptationResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    resume_id: uuid.UUID
    vacancy_id: uuid.UUID
    status: Literal["pending", "running", "done", "failed"]
    result: AdaptationResultSchema | None
    error: str | None
    created_at: datetime
