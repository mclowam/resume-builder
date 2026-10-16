import uuid
from hmac import compare_digest

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

from app.core.config import settings
from app.core.security.token import JWTTokenProvider
from app.schemas.users import UserPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
worker_token = APIKeyHeader(name="X-Worker-Token", auto_error=False)


async def get_current_worker(
    token: str | None = Depends(worker_token),
) -> None:
    expected = settings.WORKER_API_TOKEN
    if not expected:
        raise HTTPException(status_code=503, detail="Worker access is disabled")

    if not token or not compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid worker token")

def get_token_provider() -> JWTTokenProvider:
    return JWTTokenProvider()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    tokens: JWTTokenProvider = Depends(get_token_provider),
) -> UserPayload:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = tokens.decode(token, expected_type="access")
    if not payload:
        raise credentials_exception

    user_id = payload.get("user_id")
    username = payload.get("username")
    is_staff = payload.get("is_staff")
    if user_id is None or username is None:
        raise credentials_exception

    try:
        return UserPayload(
            user_id=uuid.UUID(str(user_id)),
            username=username,
            is_staff=is_staff
        )
    except (ValueError, TypeError):
        raise credentials_exception
