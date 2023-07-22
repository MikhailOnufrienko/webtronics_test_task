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


class Token(BaseModel):
    access_token: str
    refresh_token: str 


class PostBase(BaseModel):
    title: constr(max_length=120)
    content: str


class PostSingle(PostBase):
    author: str
    creation_dt: datetime


class PostUpdateResponse(BaseModel):
    title: str


class PostDeleteResponse(BaseModel):
    id: str


class PostDB(PostSingle, PostUpdateResponse, PostDeleteResponse):
    pass

class Posts(BaseModel):
    posts: list[PostDB]
