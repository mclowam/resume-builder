import uuid
from fastapi import APIRouter, Depends, HTTPException

from app.core.security.deps import get_current_user
from app.schemas.users import UserPayload
from app.schemas.resume import ResumeCreateSchema, ResumeResponseSchema
from app.services.resume import ResumeService
from app.use_cases.resume import get_resume_service


api_v1_router = APIRouter(
    prefix="/resumes"
)


@api_v1_router.post("", response_model=ResumeResponseSchema, status_code=201)
async def create_resume(
        payload: ResumeCreateSchema,
        service: ResumeService = Depends(get_resume_service),
        current_user: UserPayload = Depends(get_current_user),
):
    result = await service.create_resume(data=payload, user_id=current_user.user_id)

    return result


@api_v1_router.get("", response_model=list[ResumeResponseSchema])
async def get_resumes(
        service: ResumeService = Depends(get_resume_service),
        current_user: UserPayload = Depends(get_current_user),
):
    result = await service.get_by_user_id(user_id=current_user.user_id)

    return result


@api_v1_router.get("/{resume_id}", response_model=ResumeResponseSchema)
async def detail_resume(
        resume_id: uuid.UUID,
        service: ResumeService = Depends(get_resume_service),
        current_user: UserPayload = Depends(get_current_user),
):
    result = await service.get_by_id(resume_id=resume_id)

    if result.user_id != current_user.user_id:
        raise HTTPException(detail="Resume not found", status_code=404)

    return result
