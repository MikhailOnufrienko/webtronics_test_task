from typing import Annotated

from fastapi import Depends, Header
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis import client
from sqlalchemy.ext.asyncio import AsyncSession

from databases import get_db_session, get_redis
from src.services.post_service import PostService
from src.services.user_service import UserService
from src.schemas import (PostDeleteResponse, PostUpdateResponse,
                         Token, UserRegistration, UserLogin)
from src.schemas import PostBase, PostDB, Posts, PostSingle
from src.services.token_service import TokenService


user_router = APIRouter()

post_router = APIRouter()


@user_router.post(
    '/registration', status_code=201, summary='Регистрация нового пользователя.'
)
async def register_user(
    user: UserRegistration, db_session: AsyncSession = Depends(get_db_session)
) -> JSONResponse:
    """
    Возвращает строку с уведомлением об успешной регистрации.
    """
    success = await UserService.create_user(user, db_session)
    return JSONResponse(content=success)


@user_router.post('/login', status_code=200, summary='Вход в учётную запись.')
async def login_user(
    user: UserLogin,
    db_session: AsyncSession = Depends(get_db_session),
    cache: client.Redis = Depends(get_redis)
) -> JSONResponse:
    """
    Возвращает строку с уведомлением об успешной аутентификации.
    Заголовки 'X-Access-Token' и 'X-Refresh-Token' содержат соответствующие токены.
    """
    success, headers = await UserService.login_user(user, db_session, cache)
    return JSONResponse(content=success, headers=headers)


@user_router.post('/logout', status_code=200, summary='Выход из учётной записи.')
async def logout_user(
    tokens: Token,
    cache: client.Redis = Depends(get_redis)
) -> JSONResponse:
    """
    Возвращает строку с уведомлением о выходе из учётной записи.
    """
    success = await UserService.logout_user(tokens, cache)
    return JSONResponse(content=success)


@user_router.post(
    '/{user_id}/refresh-tokens',
    response_model=Token,
    status_code=201,
    summary='Запрос на обновление токенов.'
)
async def refresh_tokens(
    user_id: str, tokens: Token,
    cache: client.Redis = Depends(get_redis)
) -> Token:
    """
    Возвращает новые токены с параметрами:
    - **access_token**: новый токен для авторизации
    - **refresh_token**: новый токен для обновления токена авторизации

    """
    new_access_token, new_refresh_roken = await TokenService.refresh_tokens(
        user_id, tokens.access_token, tokens.refresh_token, cache
    )
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_roken
    )


@post_router.get(
    '/post', response_model=Posts, status_code=200, summary='Просмотр списка постов.'
)
async def get_posts(
    db_session: AsyncSession = Depends(get_db_session),
    cache: client.Redis = Depends(get_redis)
) -> Posts:
    """
    Возвращает список постов с параметрами:
    - **id**: ID поста
    - **title**: название поста
    - **author_id**: ID автора поста
    - **creation_dt**: дата и время создания поста
    - **like_count**: количество лайков поста
    - **dislike_count**: количество дизлайков поста

    """
    posts = await PostService.get_posts(db_session, cache)
    return Posts(posts=posts)


@post_router.get(
    '/post/{post_id}',
    response_model=PostSingle,
    status_code=200,
    summary='Просмотр одного поста.'
)
async def get_post(
    post_id: str,
    db_session: AsyncSession = Depends(get_db_session),
    cache: client.Redis = Depends(get_redis)
) -> PostSingle:
    """
    Возвращает список постов с параметрами:
    - **title**: название поста
    - **content**: содержание поста
    - **author_id**: ID автора поста
    - **creation_dt**: дата и время создания поста
    - **like_count**: количество лайков поста
    - **dislike_count**: количество дизлайков поста

    """
    post = await PostService.get_post(post_id, db_session, cache)
    return post


@post_router.post(
    '/post', response_model=PostDB, status_code=201, summary='Создание поста.'
)
async def create_post(
    post: PostBase,
    authorization: Annotated[str, Header()],
    db_session: AsyncSession = Depends(get_db_session)
    ) -> PostDB:
    """
    Возвращает информацию о созданном посте с параметрами:
    - **id**: ID поста
    - **title**: название поста
    - **author_id**: ID автора поста
    - **creation_dt**: дата и время создания поста

    """
    response = await PostService.create_and_publish_post(post, authorization, db_session)
    return response


@post_router.patch(
    '/post/{post_id}',
    response_model=PostUpdateResponse,
    status_code=200,
    summary='Изменение поста.'
)
async def update_post(
    post_id: str,
    post: PostBase,
    authorization: Annotated[str, Header()],
    db_session: AsyncSession = Depends(get_db_session)
) -> PostUpdateResponse:
    """
    Возвращает информацию об изменённом посте с параметрами:
    - **title**: название поста

    """
    response = await PostService.update_post(post_id, post, authorization, db_session)
    return response


@post_router.delete(
    '/post/{post_id}',
    response_model=PostDeleteResponse,
    status_code=200,
    summary='Удаление поста.'
)
async def delete_post(
    post_id: str,
    authorization: Annotated[str, Header()],
    db_session: AsyncSession = Depends(get_db_session)
) -> PostDeleteResponse:
    """
    Возвращает информацию об удалённом посте с параметрами:
    - **id**: ID поста

    """
    response = await PostService.delete_post(post_id, authorization, db_session)
    return response


@post_router.post(
    '/post/{post_id}/like', status_code=200, summary='Добавление лайка посту.'
)
async def like_post(
    post_id: str,
    authorization: Annotated[str, Header()],
    db_session: AsyncSession = Depends(get_db_session),
    cache: client.Redis = Depends(get_redis)
) -> str:
    """
    Возвращает строку с уведомлением об успешном добавлении лайка.
    """
    success = await PostService.like_post(
        post_id, authorization, db_session, cache
    )
    return success


@post_router.post(
    '/post/{post_id}/dislike', status_code=200, summary='Добавление дизлайка посту.'
)
async def dislike_post(
    post_id: str,
    authorization: Annotated[str, Header()],
    db_session: AsyncSession = Depends(get_db_session),
    cache: client.Redis = Depends(get_redis)
) -> str:
    """
    Возвращает строку с уведомлением об успешном добавлении дизлайка.
    """
    success = await PostService.dislike_post(
        post_id, authorization, db_session, cache
    )
    return success
