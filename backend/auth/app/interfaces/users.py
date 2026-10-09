import uuid
from typing import Any, Protocol
from app.models.users import User
from app.schemas.users import UserResponseSchema


class IUserRepository(Protocol):
    async def add(self, user: User):
        pass

    async def users(self) -> list[UserResponseSchema]:
        pass

    async def user_by_username(self, username: str):
        pass

    async def user_exists(self, username: str):
        pass

    async def get_user_by_id(self, id: uuid.UUID):
        pass

    # async def update(self, user_id: uuid.UUID, update_values: dict[str, Any]):
    #     pass