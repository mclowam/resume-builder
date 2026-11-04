import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator


class AdaptationCreateSchema(BaseModel, extra="forbid"):
    resume_id: uuid.UUID
    vacancy_id: uuid.UUID


class AdaptationReviewSchema(BaseModel, extra="forbid"):
    passed: StrictBool
    issues: list[str]

    @model_validator(mode="after")
    def validate_review(self):
        if self.passed != (not self.issues) or any(not issue.strip() for issue in self.issues):
            raise ValueError("Review verdict must agree with issues")
        return self


class AdaptationResultSchema(BaseModel, extra="forbid"):
    resume_text: str = Field(pattern=r"\S")
    review: AdaptationReviewSchema


class AdaptationFinishSchema(BaseModel, extra="forbid"):
    status: Literal["done", "failed"]
    result: AdaptationResultSchema | None = None
    error: str | None = Field(default=None, pattern=r"\S")

    @model_validator(mode="after")
    def validate_result(self):
        if self.status == "done" and (self.result is None or self.error is not None):
            raise ValueError("Completed adaptation requires result and no error")
        if self.status == "failed" and (self.error is None or self.result is not None):
            raise ValueError("Failed adaptation requires error and no result")
        return self


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
