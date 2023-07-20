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
    access_token: str


class PostDB(BaseModel):
    id: str
    title: str
    author_id: str
    creation_dt: datetime


class Posts(BaseModel):
    posts: list[PostDB]


class PostSingle(BaseModel):
    title: str
    content: str
    author: str
    creation_dt: datetime


class PostUpdate(BaseModel):
    title: str
    content: str


class Token(BaseModel):
    access_token: str
    refresh_token: str  


class PostUpdateDeleteResponse(BaseModel):
    title: str
    new_tokens: Token | None


class UserLogout(BaseModel):
    access_token: str
    refresh_token: str


class ResponseAndTokens(BaseModel):
    response: str
    access_token: str
    refresh_token: str

class RefreshToken(BaseModel):
    refresh_token: str
