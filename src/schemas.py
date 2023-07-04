from datetime import datetime

from pydantic import BaseModel
from pydantic import constr, EmailStr


class UserLogin(BaseModel):
    login: str
    password: constr(min_length=8, max_length=50)


class UserRegistration(UserLogin):
    first_name: str | None
    last_name: str | None
    email: EmailStr


class UserDB(UserRegistration):
    id: str


class PostBase(BaseModel):
    title: constr(max_length=120)
    content: str


class PostDB(BaseModel):
    id: str
    title: constr(max_length=120)
    content: str
    author_id: str
    creation_dt: datetime
    likes_count: int
    dislikes_count: int


class TokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(TokenRequest):
    access_token: str
