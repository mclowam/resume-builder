import uuid
from typing import Literal

from pydantic import BaseModel


class ResumeUploadedEvent(BaseModel):
    event_type: Literal["resume.uploaded"] = "resume.uploaded"
    resume_id: uuid.UUID
    user_id: uuid.UUID


class VacancyUploadedEvent(BaseModel):
    event_type: Literal["vacancy.uploaded"] = "vacancy.uploaded"
    vacancy_id: uuid.UUID
    user_id: uuid.UUID


class AdaptationRequestedEvent(BaseModel):
    event_type: Literal["adaptation.requested"] = "adaptation.requested"
    adaptation_id: uuid.UUID
    user_id: uuid.UUID



