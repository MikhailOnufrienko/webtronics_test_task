from typing import Annotated

from fastapi import Header, Response
from fastapi import APIRouter, Depends
from redis import client
from src.schemas import PostUpdate, Token, UserDB, UserLogout, UserRegistration, UserLogin
from src.schemas import PostBase, PostDB, Posts, PostSingle
from sqlalchemy.ext.asyncio import AsyncSession

from databases import get_db_session
from src.service import PostService, UserService
from src.utils import TokenService


user_router = APIRouter()

post_router = APIRouter()


@user_router.post('/registration', status_code=201)
async def register_user(
    user: UserRegistration, db_session: AsyncSession = Depends(get_db_session)
) -> Response:
    response = await UserService.create_user(user, db_session)
    return response


@user_router.post('/login', status_code=200)
async def login_user(user: UserLogin) -> Response:
    response = await UserService.login_user(user)
    return response


@user_router.post('/logout', status_code=200)
async def logout_user(user_logout: UserLogout, cache: client.Redis) -> str:
    response = await UserService.logout_user(user_logout, cache)
    return response


@user_router.post(
        '/{user_id}/refresh-token',
        response_model=Token,
        status_code=201
)
async def refresh_tokens(user_id: str, token_request: Token) -> Token:
    new_access_token, new_refresh_roken = await TokenService.refresh_tokens(
        user_id, token_request.access_token, token_request.refresh_token
    )
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_roken
    )


@post_router.get('/posts', response_model=Posts, status_code=200)
async def posts(db_session: AsyncSession = Depends(get_db_session)) -> list[PostDB]:
    response = await PostService.get_posts(db_session)
    return response


@post_router.get('/posts/{post_id}', response_model=PostSingle, status_code=200)
async def get_post(
    post_id: str, db_session: AsyncSession = Depends(get_db_session)
) -> PostSingle:
    response = await PostService.get_post(post_id, db_session)
    return response


@post_router.post('/posts', response_model=PostDB, status_code=201)
async def create_post(
    post: PostBase, db_session: AsyncSession = Depends(get_db_session)
    ) -> PostDB:
    response = await PostService.create_and_publish_post(post, db_session)
    return response


@post_router.patch('/posts/{post_id}', status_code=201)
async def update_post(
    post_id: str,
    post: PostUpdate,
    authorization: Annotated[str, Header()],
    db_session: AsyncSession = Depends(get_db_session)
) -> str:
    response = await PostService.update_post(post_id, post, authorization, db_session)
    return response


@post_router.delete('/posts/<post_id>')
async def delete_post():
    pass
