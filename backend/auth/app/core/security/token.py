import uuid
from datetime import datetime, timedelta, timezone
import jwt
from jwt import InvalidTokenError
from app.core.config import settings


class JWTTokenProvider:
    def __init__(
        self,
        secret_key: str = settings.SECRET_KEY,
        algorithm: str = settings.ALGORITHM,
        access_expire_min: int = settings.ACCESS_EXPIRE_MIN,
        refresh_expire_days: int = settings.REFRESH_EXPIRE_DAYS,
    ) -> None:
        if not secret_key:
            raise ValueError("SECRET_KEY must be set for JWT")
        self._secret = secret_key
        self._alg = algorithm
        self._access_expire = timedelta(minutes=access_expire_min)
        self._refresh_expire = timedelta(days=refresh_expire_days)

    def _encode(self, payload: dict, expires_in: timedelta) -> str:
        now = datetime.now(timezone.utc)
        to_encode = {
            **payload,
            "iat": now,
            "exp": now + expires_in,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(to_encode, self._secret, algorithm=self._alg)

    def create_access_token(self, payload: dict) -> str:
        return self._encode({**payload, "type": "access"}, self._access_expire)

    def create_refresh_token(self, user_id: uuid.UUID) -> str:
        return self._encode(
            {"sub": str(user_id), "type": "refresh"},
            self._refresh_expire,
        )

    def decode(self, token: str, expected_type: str | None = None) -> dict | None:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._alg])
        except InvalidTokenError:
            return None
        if expected_type and payload.get("type") != expected_type:
            return None
        return payload