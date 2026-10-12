from fastapi import Depends

from app.db.session import SessionDep
from app.interfaces.event_publisher import IEventPublisher
from app.repositories.vacancy import VacancyRepository
from app.services.vacancy import VacancyService
from app.use_cases.event_publisher import get_event_publisher


def get_vacancy_repository(session: SessionDep) -> VacancyRepository:
    return VacancyRepository(session)


def get_vacancy_service(
        vacancy_repository: VacancyRepository = Depends(get_vacancy_repository),
        event_publisher: IEventPublisher = Depends(get_event_publisher),
) -> VacancyService:
    return VacancyService(
        vacancy_repository=vacancy_repository,
        event_publisher=event_publisher,
    )
