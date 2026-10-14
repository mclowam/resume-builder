from fastapi import Depends

from app.core.config import settings
from app.db.session import SessionDep
from app.interfaces.image_storage import IImageStorage
from app.repositories.resume import ResumeRepository
from app.repositories.storage.image_storage import ImageStorage
from app.services.resume import ResumeService


def get_resume_repository(session: SessionDep) -> ResumeRepository:
    return ResumeRepository(session)


def get_file_storage() -> IImageStorage:
    return ImageStorage(settings)


def get_resume_service(
        resume_repository: ResumeRepository = Depends(get_resume_repository),
        file_storage: IImageStorage = Depends(get_file_storage),
) -> ResumeService:
    return ResumeService(
        resume_repository=resume_repository,
        file_storage=file_storage,
    )
