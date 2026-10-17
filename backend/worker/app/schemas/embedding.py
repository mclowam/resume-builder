from pydantic import BaseModel


class PatchEmbeddingSchema(BaseModel):
    embedding: list[float]
