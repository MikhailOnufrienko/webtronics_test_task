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


class PostLikeDislikeMixin(BaseModel):
    like_count: int
    dislike_count: int


class PostSingle(PostBase, PostLikeDislikeMixin):
    author: str
    creation_dt: datetime


class PostUpdateResponse(BaseModel):
    title: str


class PostDeleteResponse(BaseModel):
    id: str


class PostDB(BaseModel):
    id: str
    title: str
    author_id: str
    creation_dt: datetime


class PostDBLikeDislike(PostDB, PostLikeDislikeMixin):
    pass
    

class Posts(BaseModel):
    posts: list[PostDBLikeDislike]
