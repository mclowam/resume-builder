import uuid

from pydantic import BaseModel


class VacancyCreateSchema(BaseModel):
    user_id: uuid.UUID
    content: str


class VacancyResponseSchema(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    content: str