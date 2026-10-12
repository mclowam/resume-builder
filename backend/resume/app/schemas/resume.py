import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ResumeCreateSchema(BaseModel):
    image_url: str
    embedding: Optional[list[float]] = None


class ResumeResponseSchema(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    image_url: str
    embedding: Optional[list[float]] = None
    created_at: datetime
