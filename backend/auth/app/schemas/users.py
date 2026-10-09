import uuid

from pydantic import BaseModel


class UserPayload(BaseModel):
    user_id: uuid.UUID
    username: str
    is_staff: bool


class UserCreateSchema(BaseModel):
    username: str
    password: str


class UserResponseSchema(BaseModel):
    user_id: uuid.UUID
    username: str
    is_active: bool
    is_staff: bool


class UserLoginSchema(BaseModel):
    username: str
    password: str


class LoginResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshTokenSchema(BaseModel):
    refresh_token: str

class UserPostCreateSchema(BaseModel):
    user_id: uuid.UUID
    username: str

class UpdateUserSchema(BaseModel):
    username: str | None = None
    password: str | None = None