from fastapi import Depends

from app.db.session import SessionDep
from app.interfaces.event_publisher import IEventPublisher
from app.repositories.resume import ResumeRepository
from app.services.resume import ResumeService
from app.use_cases.event_publisher import get_event_publisher


def get_resume_repository(session: SessionDep) -> ResumeRepository:
    return ResumeRepository(session)


def get_resume_service(
        resume_repository: ResumeRepository = Depends(get_resume_repository),
        event_publisher: IEventPublisher = Depends(get_event_publisher),
) -> ResumeService:
    return ResumeService(
        resume_repository=resume_repository,
        event_publisher=event_publisher,
    )
