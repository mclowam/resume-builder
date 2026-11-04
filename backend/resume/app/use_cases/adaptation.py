from fastapi import Depends

from app.db.session import SessionDep
from app.repositories.adaptation import AdaptationRepository
from app.repositories.resume import ResumeRepository
from app.repositories.vacancy import VacancyRepository
from app.services.adaptation import AdaptationService
from app.use_cases.resume import get_resume_repository
from app.use_cases.vacancy import get_vacancy_repository


def get_adaptation_repository(session: SessionDep) -> AdaptationRepository:
    return AdaptationRepository(session)


def get_adaptation_service(
        adaptation_repository: AdaptationRepository = Depends(get_adaptation_repository),
        resume_repository: ResumeRepository = Depends(get_resume_repository),
        vacancy_repository: VacancyRepository = Depends(get_vacancy_repository),
) -> AdaptationService:
    return AdaptationService(adaptation_repository, resume_repository, vacancy_repository)
