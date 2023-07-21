import json
import uuid
from typing import Annotated

from fastapi import HTTPException, Header, Response
from fastapi.responses import JSONResponse
from redis import client
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import joinedload
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from werkzeug.security import generate_password_hash, check_password_hash

from src.schemas import PostUpdate, ResponseAndTokens, UserLogin, UserLogout, UserRegistration
from src.models import Post
from src.schemas import PostBase, PostDB, Posts, PostSingle
from src.models import User
from databases import get_db_session
from src.utils import TokenService
from config import settings


class UserService:

    @staticmethod
    async def create_user(user: UserRegistration, db_session: AsyncSession) -> Response:
        if (not await UserService.check_login_exists(user.login)
            and not await UserService.check_email_exists(user.email)):
            success_text = await UserService.save_user_to_database(user, db_session)
            return Response(content=success_text, status_code=201)

    @staticmethod
    async def check_login_exists(login: str) -> bool:
        async for session in get_db_session():
            query = select(User.login).filter(User.login == login)
            result = await session.execute(query)
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail='Пользователь с таким логином уже зарегистрирован.'
                )
            return False
        
    @staticmethod
    async def check_email_exists(email: str) -> bool:
            async for session in get_db_session():
                query = select(User.email).filter(User.email == email)
                result = await session.execute(query)
                if result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=400,
                        detail='Пользователь с таким email уже зарегистрирован.'
                    )
            return False
    
    @staticmethod
    async def save_user_to_database(user: UserRegistration, db_session: AsyncSession) -> str:
        hashed_password = generate_password_hash(user.password)
        new_user = User(
            login=user.login,
            hashed_password=hashed_password,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email
        )
        db_session.add(new_user)
        await db_session.commit()
        return "Вы успешно зарегистрировались."
    
    @staticmethod
    async def login_user(user: UserLogin) -> Response:
        if await UserService.check_credentials_correct(user.login, user.password):
            user_id = await UserService.get_user_id_by_login(user)
            access_token, refresh_token = await TokenService.generate_tokens(user_id)
            await TokenService.save_refresh_token_to_cache(user_id, refresh_token)
            content = json.dumps({
                'user_id': user_id,
                'access_token': access_token,
                'refresh_token': refresh_token
            })
            response = Response(status_code=200, content=content)
            response.headers['Content-Type'] = 'application/json'
            return response
    
    @staticmethod
    async def check_credentials_correct(login: str, password: str) -> bool:
        query_for_login = select(User.login).filter(User.login == login)
        async for session in get_db_session():
            result = await session.execute(query_for_login)
            if result.scalar_one_or_none():
                print(result)
                query_for_password = select(
                    User.hashed_password
                ).filter(User.login == login)
                result = await session.execute(query_for_password)
                hashed_password = result.scalar_one()
                if check_password_hash(hashed_password, password):
                    return True
            raise HTTPException(status_code=401, detail='Логин или пароль не верен.')
        
    @staticmethod
    async def get_user_id_by_login(user: UserLogin) -> str:
        query = select(User.id).filter(User.login == user.login)
        async for session in get_db_session():
            result = await session.execute(query)
            user_id = result.scalar_one()
            return str(user_id)
        
    @staticmethod
    async def logout_user(user: UserLogout, cache: client.Redis) -> str:
        await TokenService.add_invalid_access_token_to_cache(user.access_token, cache)
        user_id = await TokenService.get_user_id_by_token(user.access_token)
        await TokenService.delete_refresh_token_from_cache(cache, user_id)
        return 'Вы успешно вышли из учётной записи.'


class PostService:

    @staticmethod
    async def create_and_publish_post(
        post: PostBase, authorization: Annotated[str, Header()], db_session: AsyncSession
    ) -> PostDB:
        access_token = await TokenService.get_token_authorization(authorization)
        validation_result = await TokenService.check_access_token_valid_or_return_new_tokens(access_token)
        if validation_result:
            author_id = await TokenService.get_user_id_by_token(access_token)
            new_post = Post(
                title=post.title,
                content=post.content,
                author_id=author_id
            )
            db_session.add(new_post)
            await db_session.commit()
            new_post_id_as_str = str(new_post.id)
            creation_dt_as_string = json.dumps(new_post.creation_dt, default=str)
            content = {'id': new_post_id_as_str,
                'title': new_post.title,
                'author_id': new_post.author_id,
                'creation_dt': creation_dt_as_string}
            headers = {
                'X-Access-Token': validation_result[0],
                'X-Refresh-Token': validation_result[1]
            }
            return JSONResponse(content=content, headers=headers)

    @staticmethod
    async def get_post(post_id: str, db_session: AsyncSession) -> PostSingle:
        query = select(Post).filter(Post.id == post_id)
        query = query.options(joinedload(Post.author))
        result = await db_session.execute(query)
        post = result.scalar()
        if not post:
            raise HTTPException(status_code=404, detail='Запись не найдена.')
        author_name = post.author.login
        return PostSingle(
            title=post.title,
            content=post.content,
            author=author_name,
            creation_dt=post.creation_dt
        )

    @staticmethod
    async def get_posts(db_session: AsyncSession) -> Posts:
        query = select(Post)
        result = await db_session.execute(query)
        posts = result.scalars().all()
        return Posts(posts=[
            {'id': str(post.id),
            'title': post.title,
            'author_id': str(post.author_id),
            'creation_dt': post.creation_dt} for post in posts
        ] if posts else [])
    
    @staticmethod
    async def update_post(
        post_id: str,
        post_update: PostUpdate,
        authorization: Annotated[str, Header()],
        db_session: AsyncSession
    ) -> dict[str, str]:
        access_token = await TokenService.get_token_authorization(authorization)
        validation_result = await TokenService.check_access_token_valid_or_return_new_tokens(access_token)
        if validation_result:    
            query = select(Post).filter(Post.id == post_id)
            result = await db_session.execute(query)
            post = result.one_or_none()
            if not post:
                raise HTTPException(status_code=404, detail="Запись не найдена.")
            post_table = Post.__table__
            upd_query = (update(post_table).
                where(post_table.c.id == uuid.UUID(post_id)).
                values({
                    post_table.c.title: post_update.title,
                    post_table.c.content: post_update.content
                })
            )
            await db_session.execute(upd_query)
            await db_session.commit()
            return {
                'title': post_update.title
            } if isinstance(validation_result, bool) else {
                'title': post_update.title,
                'access_token': validation_result[0],
                'refresh_token': validation_result[1]
            }

    @staticmethod
    async def delete_post(
        post_id: str,
        authorization: Annotated[str, Header()],
        db_session: AsyncSession
    ) -> dict[str, str]:
        access_token = await TokenService.get_token_authorization(authorization)
        validation_result = await TokenService.check_access_token_valid_or_return_new_tokens(access_token)
        if validation_result:    
            query = select(Post).filter(Post.id == post_id)
            result = await db_session.execute(query)
            post = result.one_or_none()
            if not post:
                raise HTTPException(status_code=404, detail="Запись не найдена.")
            post_table = Post.__table__
            delete_query = (delete(post_table).
                            where(post_table.c.id == uuid.UUID(post_id)))
            await db_session.execute(delete_query)
            await db_session.commit()
            return {
                'post_id': post_id
            } if isinstance(validation_result, bool) else {
                'post_id': post_id,
                'access_token': validation_result[0],
                'refresh_token': validation_result[1]
            }
