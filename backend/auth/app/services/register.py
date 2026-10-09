from fastapi import HTTPException

from app.core.security.password import PasswordHashed
from app.models.users import User
from app.services.users_abc import IUserRepository


class RegisterService:
    def __init__(
            self,
            user: IUserRepository,
            hasher: PasswordHashed,
    ):
        self._user = user
        self._hasher = hasher

    async def register(
            self,
            username: str,
            password: str,
    ) -> User:
        if await self._user.user_exists(username):
            raise HTTPException(status_code=400, detail="Username already registered")

        password_hash = self._hasher.hash(password)

        user = User(
            username=username,
            password_hash=password_hash,
        )

        return await self._user.add(user)