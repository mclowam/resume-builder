import uuid

from fastapi import APIRouter, Depends, Response

from app.core.security.deps import get_current_user
from app.schemas.adaptation import AdaptationCreateSchema, AdaptationResponseSchema
from app.schemas.users import UserPayload
from app.services.adaptation import AdaptationService
from app.use_cases.adaptation import get_adaptation_service


api_v1_router = APIRouter(prefix="/adaptations")


@api_v1_router.post("", response_model=AdaptationResponseSchema, status_code=201)
async def create_adaptation(
        payload: AdaptationCreateSchema,
        response: Response,
        service: AdaptationService = Depends(get_adaptation_service),
        current_user: UserPayload = Depends(get_current_user),
):
    result = await service.create_adaptation(payload, current_user.user_id)
    response.headers["Location"] = f"/adaptations/{result.id}"
    return result


@api_v1_router.get("/{adaptation_id}", response_model=AdaptationResponseSchema)
async def detail_adaptation(
        adaptation_id: uuid.UUID,
        service: AdaptationService = Depends(get_adaptation_service),
        current_user: UserPayload = Depends(get_current_user),
):
    return await service.get_by_id(adaptation_id, current_user.user_id)
