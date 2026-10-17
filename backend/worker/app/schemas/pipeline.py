import uuid
from typing import Literal

from pydantic import BaseModel


class DocumentEmbedding(BaseModel):
    document_id: uuid.UUID
    user_id: uuid.UUID
    document_type: Literal["resume", "vacancy"]
    text: str
    embedding: list[float]
    embedding_model: str
