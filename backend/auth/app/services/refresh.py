import uuid

from app.core.security.token import JWTTokenProvider
from app.services.errors import InvalidRefreshTokenError
from app.services.payload import build_access_payload
from app.services.users_abc import IUserRepository


class RefreshService:
    def __init__(
        self,
        users: IUserRepository,
        tokens: JWTTokenProvider,
    ) -> None:
        self._users = users
        self._tokens = tokens

    async def refresh(self, refresh_token: str) -> dict:
        payload = self._tokens.decode(refresh_token, expected_type="refresh")
        if not payload or not payload.get("sub"):
            raise InvalidRefreshTokenError("Invalid refresh token")

        try:
            user_id = uuid.UUID(payload["sub"])
        except (ValueError, TypeError) as exc:
            raise InvalidRefreshTokenError("Invalid refresh token") from exc

        user = await self._users.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise InvalidRefreshTokenError("User not found or inactive")

        access = self._tokens.create_access_token(build_access_payload(user))
        new_refresh = self._tokens.create_refresh_token(user.user_id)
        return {
            "access_token": access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
        }