import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ResumeCreateSchema(BaseModel):
    file_url: str
    embedding: Optional[list[float]] = None


class ResumeResponseSchema(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    file_url: str
    embedding: Optional[list[float]] = None
    created_at: datetime


class ResumeSetEmbeddingSchema(BaseModel):
    embedding: Optional[list[float]]
