import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.security.deps import get_current_worker
from app.schemas.vacancy import VacancyResponseSchema, VacancySetEmbeddingSchema
from app.services.resume import ResumeService
from app.services.vacancy import VacancyService
from app.use_cases.resume import get_resume_service
from app.use_cases.vacancy import get_vacancy_service


api_v1_router = APIRouter(
    prefix="/internal",
    dependencies=[Depends(get_current_worker)],
)


@api_v1_router.get("/resumes/{resume_id}", response_class=Response)
async def get_resume_file(
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
        service: ResumeService = Depends(get_resume_service),
):
    data, content_type, filename = await service.get_file(
        resume_id=resume_id,
        user_id=user_id,
    )

    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='')}"},
    )


@api_v1_router.get("/vacancies/{vacancy_id}", response_model=VacancyResponseSchema)
async def get_vacancy(
        vacancy_id: uuid.UUID,
        user_id: uuid.UUID,
        service: VacancyService = Depends(get_vacancy_service),
):
    result = await service.get_by_id(vacancy_id=vacancy_id)
    if result.user_id != user_id:
        raise HTTPException(detail="Vacancy not found", status_code=404)

    return result


@api_v1_router.patch("/vacancies/{vacancy_id}", response_model=VacancyResponseSchema, status_code=200)
async def set_embedding_vacancy(
        vacancy_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: VacancySetEmbeddingSchema,
        service: VacancyService = Depends(get_vacancy_service),
):
    vacancy = await service.get_by_id(vacancy_id=vacancy_id)
    if vacancy.user_id != user_id:
        raise HTTPException(detail="Vacancy not found", status_code=404)

    result = await service.set_embedding(vacancy_id=vacancy_id, data=payload)
    return result
