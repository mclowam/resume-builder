import uuid
from fastapi import APIRouter, Depends, HTTPException

from app.core.security.deps import get_current_user
from app.schemas.users import UserPayload
from app.schemas.vacancy import VacancyCreateSchema, VacancyResponseSchema
from app.services.vacancy import VacancyService
from app.use_cases.vacancy import get_vacancy_service


api_v1_router = APIRouter(
    prefix="/vacancies"
)


@api_v1_router.post("", response_model=VacancyResponseSchema, status_code=201)
async def create_vacancy(
        payload: VacancyCreateSchema,
        service: VacancyService = Depends(get_vacancy_service),
        current_user: UserPayload = Depends(get_current_user),
):
    result = await service.create_vacancy(data=payload, user_id=current_user.user_id)

    return result


@api_v1_router.get("", response_model=list[VacancyResponseSchema])
async def get_vacancies(
        service: VacancyService = Depends(get_vacancy_service),
        current_user: UserPayload = Depends(get_current_user),
):
    result = await service.get_by_user_id(user_id=current_user.user_id)

    return result


@api_v1_router.get("/{vacancy_id}", response_model=VacancyResponseSchema)
async def detail_vacancy(
        vacancy_id: uuid.UUID,
        service: VacancyService = Depends(get_vacancy_service),
        current_user: UserPayload = Depends(get_current_user),
):
    result = await service.get_by_id(vacancy_id=vacancy_id)

    if result.user_id != current_user.user_id:
        raise HTTPException(detail="Vacancy not found", status_code=404)

    return result
