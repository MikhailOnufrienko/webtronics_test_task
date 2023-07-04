from fastapi import Response
from fastapi import APIRouter, Depends
from src.schemas import UserRegistration, UserLogin, Post
from sqlalchemy.ext.asyncio import AsyncSession

from databases import get_db_session
from service import UserService


router = APIRouter()

route_prefix: str = '/api/v1/auth'


@router.post('/signup', status_code=201)
async def register_user(
    user: UserRegistration, db: AsyncSession = Depends(get_db_session)
) -> Response:
    response = await UserService.create_user(user, db)
    return response


@router.post('/login', status_code=200)
async def login_user(
    user: UserLogin, db: AsyncSession = Depends(get_db_session)
) -> Response:
    response = await UserService.login_user(user, db)
    return response
