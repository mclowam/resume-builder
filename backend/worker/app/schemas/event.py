import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ResumeUploadedData(BaseModel):
    resume_id: uuid.UUID
    user_id: uuid.UUID


class VacancyUploadedData(BaseModel):
    vacancy_id: uuid.UUID
    user_id: uuid.UUID


class ResumeUploadedEvent(BaseModel):
    event_type: Literal["resume.uploaded"]
    data: ResumeUploadedData


class VacancyUploadedEvent(BaseModel):
    event_type: Literal["vacancy.uploaded"]
    data: VacancyUploadedData


class AdaptationRequestedData(BaseModel):
    adaptation_id: uuid.UUID
    user_id: uuid.UUID


class AdaptationRequestedEvent(BaseModel):
    event_type: Literal["adaptation.requested"]
    data: AdaptationRequestedData


Event = Annotated[
    ResumeUploadedEvent | VacancyUploadedEvent | AdaptationRequestedEvent,
    Field(discriminator="event_type"),
]
