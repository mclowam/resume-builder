from fastapi import Depends

from app.db.session import SessionDep
from app.repositories.resume import ResumeRepository
from app.services.resume import ResumeService


def get_resume_repository(session: SessionDep) -> ResumeRepository:
    return ResumeRepository(session)


def get_resume_service(
        resume_repository: ResumeRepository = Depends(get_resume_repository),
) -> ResumeService:
    return ResumeService(
        resume_repository=resume_repository,
    )
