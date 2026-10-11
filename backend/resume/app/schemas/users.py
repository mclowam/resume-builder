import uuid

from pydantic import BaseModel


class UserPayload(BaseModel):
    user_id: uuid.UUID
    username: str
    is_staff: bool
