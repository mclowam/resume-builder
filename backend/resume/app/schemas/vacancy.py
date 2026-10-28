import uuid
from typing import Optional

from pydantic import BaseModel


class VacancyCreateSchema(BaseModel):
    text: str


class VacancyResponseSchema(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    text: str
    embedding: Optional[list[float]] = None


class VacancySetEmbeddingSchema(BaseModel):
    embedding: Optional[list[float]]
