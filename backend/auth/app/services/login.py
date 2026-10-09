from fastapi import HTTPException
from app.core.security.password import PasswordHashed
from app.schemas.users import UserLoginSchema
from app.services.payload import build_access_payload
from app.interfaces.users import IUserRepository


class LoginService:
    def __init__(
            self,
            users: IUserRepository,
            hasher: PasswordHashed,
            tokens: JWTTokenProvider

    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    async def login(self, data: UserLoginSchema):
        user = await self._users.user_by_username(data.username)
        if not user or not self._hasher.verify(data.password, user.password_hash):
            raise HTTPException(detail="Invalid username or password", status_code=401)

        if not user.is_active:
            raise HTTPException(detail="Inactive user", status_code=401)

        access = self._tokens.create_access_token(build_access_payload(user))
        refresh = self._tokens.create_refresh_token(user.id)

        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
        }