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


class Token(BaseModel):
    access_token: str
    refresh_token: str  
