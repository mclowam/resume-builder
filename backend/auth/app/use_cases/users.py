from fastapi import Depends

from app.core.security.password import PasswordHashed
from app.core.security.token import JWTTokenProvider
from app.db.session import SessionDep
from app.repositories.users import UserRepository
from app.services.login import LoginService
from app.services.refresh import RefreshService
from app.services.register import RegisterService
from app.services.users import UserService

_hasher = PasswordHashed()
_tokens = JWTTokenProvider()


def get_password_hasher() -> PasswordHashed:
    return _hasher


def get_user_repository(session: SessionDep) -> UserRepository:
    return UserRepository(session)


def get_token_provider() -> JWTTokenProvider:
    return _tokens


def get_register_service(
        user: UserRepository = Depends(get_user_repository),
        hasher: PasswordHashed = Depends(get_password_hasher),

) -> RegisterService:
    return RegisterService(
        user=user,
        hasher=hasher,
    )


def get_login_service(
        users: UserRepository = Depends(get_user_repository),
        hasher: PasswordHashed = Depends(get_password_hasher),
        tokens: JWTTokenProvider = Depends(get_token_provider),
) -> LoginService:
    return LoginService(
        users=users,
        hasher=hasher,
        tokens=tokens,
    )





def get_user_service(
        users: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(
        users=users,
    )


def get_refresh_service(
        users: UserRepository = Depends(get_user_repository),
        tokens: JWTTokenProvider = Depends(get_token_provider)
) -> RefreshService:
    return RefreshService(
        users=users,
        tokens=tokens
    )

# def get_update_user_service(
#         users: UserRepository = Depends(get_user_repository),
#         hasher: PasswordHashed = Depends(get_password_hasher),
# ) -> UserUpdateService:
#     return UserUpdateService(
#         users=users,
#         hasher=hasher,
#     )