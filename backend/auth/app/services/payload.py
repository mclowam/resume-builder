from app.models.users import User
from app.schemas.users import UserResponseSchema


def build_access_payload(user: User | UserResponseSchema) -> dict:
    user_id = user.id if isinstance(user, User) else user.user_id
    return {
        "user_id": str(user_id),
        "username": user.username,
        "is_staff": user.is_staff,
    }