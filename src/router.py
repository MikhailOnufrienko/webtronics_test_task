from typing import Annotated

from fastapi import Header
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis import client
from sqlalchemy.ext.asyncio import AsyncSession

from databases import get_db_session, get_redis
from src.service import PostService, UserService
from src.schemas import (PostDeleteResponse, PostUpdateResponse,
                         Token, UserRegistration, UserLogin)
from src.schemas import PostBase, PostDB, Posts, PostSingle
from src.utils import TokenService


user_router = APIRouter()

post_router = APIRouter()


@user_router.post('/registration', status_code=201)
async def register_user(
    user: UserRegistration, db_session: AsyncSession = Depends(get_db_session)
) -> JSONResponse:
    success = await UserService.create_user(user, db_session)
    return JSONResponse(content=success)


@user_router.post('/login', status_code=200)
async def login_user(
    user: UserLogin,
    cache: client.Redis = Depends(get_redis)
) -> JSONResponse:
    success, headers = await UserService.login_user(user, cache)
    return JSONResponse(content=success, headers=headers)


@user_router.post('/logout', status_code=200)
async def logout_user(
    tokens: Token,
    cache: client.Redis = Depends(get_redis)
) -> JSONResponse:
    success = await UserService.logout_user(tokens, cache)
    return JSONResponse(content=success)


@user_router.post(
        '/{user_id}/refresh-tokens',
        response_model=Token,
        status_code=201
)
async def refresh_tokens(
    user_id: str, tokens: Token,
    cache: client.Redis = Depends(get_redis)
) -> Token:
    new_access_token, new_refresh_roken = await TokenService.refresh_tokens(
        user_id, tokens.access_token, tokens.refresh_token, cache
    )
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_roken
    )


@post_router.get('/post', response_model=Posts, status_code=200)
async def get_posts(
    db_session: AsyncSession = Depends(get_db_session),
    cache: client.Redis = Depends(get_redis)
) -> Posts:
    posts = await PostService.get_posts(db_session, cache)
    return Posts(posts=posts)


@post_router.get('/post/{post_id}', response_model=PostSingle, status_code=200)
async def get_post(
    post_id: str,
    db_session: AsyncSession = Depends(get_db_session),
    cache: client.Redis = Depends(get_redis)
) -> PostSingle:
    post = await PostService.get_post(post_id, db_session, cache)
    return post


@post_router.post('/post', response_model=PostDB, status_code=201)
async def create_post(
    post: PostBase,
    authorization: Annotated[str, Header()],
    db_session: AsyncSession = Depends(get_db_session)
    ) -> PostDB:
    response = await PostService.create_and_publish_post(post, authorization, db_session)
    return response


@post_router.patch('/post/{post_id}', response_model=PostUpdateResponse, status_code=200)
async def update_post(
    post_id: str,
    post: PostBase,
    authorization: Annotated[str, Header()],
    db_session: AsyncSession = Depends(get_db_session)
) -> PostUpdateResponse:
    response = await PostService.update_post(post_id, post, authorization, db_session)
    return response


@post_router.delete(
    '/post/{post_id}',
    response_model=PostDeleteResponse,
    status_code=200
)
async def delete_post(
    post_id: str,
    authorization: Annotated[str, Header()],
    db_session: AsyncSession = Depends(get_db_session)
) -> PostDeleteResponse:
    response = await PostService.delete_post(post_id, authorization, db_session)
    return response


@post_router.post('/post/{post_id}/like', status_code=200)
async def like_post(
    post_id: str,
    authorization: Annotated[str, Header()],
    db_session: AsyncSession = Depends(get_db_session),
    cache: client.Redis = Depends(get_redis)
) -> str:
    success = await PostService.like_post(
        post_id, authorization, db_session, cache
    )
    return success


@post_router.post('/post/{post_id}/dislike', status_code=200)
async def dislike_post(
    post_id: str,
    authorization: Annotated[str, Header()],
    db_session: AsyncSession = Depends(get_db_session),
    cache: client.Redis = Depends(get_redis)
) -> str:
    success = await PostService.dislike_post(
        post_id, authorization, db_session, cache
    )
    return success
