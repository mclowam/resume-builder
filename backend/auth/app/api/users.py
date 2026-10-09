import uuid
from fastapi import APIRouter, Depends, HTTPException
from app.core.security.deps import get_current_user
from app.schemas.users import UserCreateSchema, UserPostCreateSchema, UserLoginSchema, LoginResponseSchema, \
    UserResponseSchema, UserPayload, RefreshTokenSchema, UpdateUserSchema
from app.services.login import LoginService
from app.services.refresh import RefreshService
from app.services.register import RegisterService
from app.services.users import UserService
from app.use_cases.users import get_register_service, get_login_service, get_user_service, get_refresh_service

api_v1_router = APIRouter(
    prefix="/auth"
)


@api_v1_router.post("/register", response_model=UserPostCreateSchema, status_code=201)
async def register_user(
        payload: UserCreateSchema,
        service: RegisterService = Depends(get_register_service),
):
    user = await service.register(username=payload.username, password=payload.password)

    return UserPostCreateSchema(user_id=user.id, username=user.username)


@api_v1_router.post("/login", response_model=LoginResponseSchema, status_code=200)
async def login(payload: UserLoginSchema,
                service: LoginService = Depends(get_login_service),
                ):
    result = await service.login(data=payload)
    return result


@api_v1_router.get("/users", response_model=list[UserResponseSchema])
async def get_users(
        service: UserService = Depends(get_user_service),
        _: UserPayload = Depends(get_current_user),
):
    result = await service.list_users()

    return result


@api_v1_router.get("/users/{user_id}", response_model=UserResponseSchema)
async def detail_user(
        user_id: uuid.UUID,
        service: UserService = Depends(get_user_service),
        _: UserPayload = Depends(get_current_user),
):
    result = await service.detail(id=user_id)

    return result


@api_v1_router.get("/me", response_model=UserPayload)
async def me(current_user: UserPayload = Depends(get_current_user)):
    return current_user


@api_v1_router.post("/refresh", response_model=LoginResponseSchema)
async def refresh(
        payload: RefreshTokenSchema,
        service: RefreshService = Depends(get_refresh_service)
):
    tokens = await service.refresh(payload.refresh_token)

    return LoginResponseSchema(**tokens)

# @api_v1_router.patch('/users', response_model=UserResponseSchema)
# async def update_user(
#         payload: UpdateUserSchema,
#         user_id: uuid.UUID,
#         service: UserUpdateService = Depends(get_update_user_service),
# ):
#     return await service.update(user_id=user_id, user_data=payload)