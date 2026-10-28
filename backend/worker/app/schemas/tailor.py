from pydantic import BaseModel, Field


class TailorResult(BaseModel, extra="forbid"):
    resume_text: str = Field(pattern=r"\S")
