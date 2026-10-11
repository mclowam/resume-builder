import uuid

from pydantic import BaseModel


class VacancyCreateSchema(BaseModel):
    text: str


class VacancyResponseSchema(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    text: str