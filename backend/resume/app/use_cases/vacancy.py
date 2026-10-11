from fastapi import Depends

from app.db.session import SessionDep
from app.repositories.vacancy import VacancyRepository
from app.services.vacancy import VacancyService


def get_vacancy_repository(session: SessionDep) -> VacancyRepository:
    return VacancyRepository(session)


def get_vacancy_service(
        vacancy_repository: VacancyRepository = Depends(get_vacancy_repository),
) -> VacancyService:
    return VacancyService(
        vacancy_repository=vacancy_repository,
    )
