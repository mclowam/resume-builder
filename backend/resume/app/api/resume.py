import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile

from app.core.security.deps import get_current_user
from app.schemas.users import UserPayload
from app.schemas.resume import ResumeResponseSchema
from app.services.resume import ResumeService
from app.use_cases.resume import get_resume_service


api_v1_router = APIRouter(
    prefix="/resumes"
)


@api_v1_router.post("", response_class=Response, status_code=201)
async def create_resume(
        request: Request,
        file: UploadFile = File(...),
        service: ResumeService = Depends(get_resume_service),
        current_user: UserPayload = Depends(get_current_user),
):
    try:
        result = await service.create_resume(file=file, user_id=current_user.user_id)
    finally:
        await file.close()

    return Response(
        status_code=201,
        headers={"Location": str(request.url_for("detail_resume", resume_id=result.id))},
    )


@api_v1_router.get("", response_model=list[ResumeResponseSchema])
async def get_resumes(
        service: ResumeService = Depends(get_resume_service),
        current_user: UserPayload = Depends(get_current_user),
):
    result = await service.get_by_user_id(user_id=current_user.user_id)

    return result


@api_v1_router.get("/{resume_id}", response_class=Response)
async def detail_resume(
        resume_id: uuid.UUID,
        service: ResumeService = Depends(get_resume_service),
        current_user: UserPayload = Depends(get_current_user),
):
    data, content_type, filename = await service.get_file(
        resume_id=resume_id,
        user_id=current_user.user_id,
    )

    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='')}"},
    )
