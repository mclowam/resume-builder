from pydantic import BaseModel, Field

from app.schemas.critic import CriticResult


class ResumeAdaptationResult(BaseModel, extra="forbid"):
    resume_text: str = Field(pattern=r"\S")
    review: CriticResult
