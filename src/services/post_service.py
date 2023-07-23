import json
import uuid
from typing import Annotated

from fastapi import HTTPException, Header
from fastapi.responses import JSONResponse
from redis import client
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import joinedload

from src.schemas import PostBase, PostSingle
from src.models import Post
from src.services.token_service import TokenService


class PostService:

    @staticmethod
    async def create_and_publish_post(
        post: PostBase, authorization: Annotated[str, Header()], db_session: AsyncSession
    ) -> JSONResponse:
        access_token = await TokenService.get_token_authorization(authorization)
        validation_result = (
            await TokenService.check_access_token_valid_or_return_new_tokens(access_token)
        )
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
            } if isinstance(validation_result, tuple) else {}
            return JSONResponse(content=content, headers=headers)

    @staticmethod
    async def get_post(post_id: str, db_session: AsyncSession, cache: client.Redis) -> PostSingle:
        query = select(Post).filter(Post.id == post_id)
        query = query.options(joinedload(Post.author))
        result = await db_session.execute(query)
        post = result.scalar()
        if not post:
            raise HTTPException(status_code=404, detail='Запись не найдена.')
        author_name = post.author.login
        like_count = await PostService.get_post_like_count(post_id, cache)
        dislike_count = await PostService.get_post_dislike_count(post_id, cache)
        return PostSingle(
            title=post.title,
            content=post.content,
            author=author_name,
            creation_dt=post.creation_dt,
            like_count=like_count,
            dislike_count=dislike_count
        )

    @staticmethod
    async def get_posts(
        db_session: AsyncSession, cache: client.Redis
    ) -> list[dict | None]:
        query = select(Post)
        result = await db_session.execute(query)
        posts = result.scalars().all()
        return [{
            'id': str(post.id),
            'title': post.title,
            'author_id': str(post.author_id),
            'creation_dt': post.creation_dt,
            'like_count': await PostService.get_post_like_count(str(post.id), cache),
            'dislike_count': await PostService.get_post_dislike_count(str(post.id), cache)
        } for post in posts] if posts else []
    
    @staticmethod
    async def update_post(
        post_id: str,
        post_to_update: PostBase,
        authorization: Annotated[str, Header()],
        db_session: AsyncSession
    ) -> JSONResponse:
        access_token = await TokenService.get_token_authorization(authorization)
        validation_result = (
            await TokenService.check_access_token_valid_or_return_new_tokens(access_token)
        )
        if validation_result:
            user_id = await TokenService.get_user_id_by_token(access_token)
            query = select(Post).filter(Post.id == post_id, Post.author_id == user_id)
            result = await db_session.execute(query)
            post = result.one_or_none()
            if not post:
                raise HTTPException(
                    status_code=404,
                    detail="Запись не найдена либо изменить запись может только автор."
                )
            post_table = Post.__table__
            upd_query = (update(post_table).
                where(post_table.c.id == uuid.UUID(post_id)).
                values({
                    post_table.c.title: post_to_update.title,
                    post_table.c.content: post_to_update.content
                })
            )
            await db_session.execute(upd_query)
            await db_session.commit()
            content = {'title': post_to_update.title}
            headers = {
                'X-Access-Token': validation_result[0],
                'X-Refresh-Token': validation_result[1]
            } if isinstance(validation_result, tuple) else {}
            return JSONResponse(content=content, headers=headers)

    @staticmethod
    async def delete_post(
        post_id: str,
        authorization: Annotated[str, Header()],
        db_session: AsyncSession
    ) -> JSONResponse:
        access_token = await TokenService.get_token_authorization(authorization)
        validation_result = (
            await TokenService.check_access_token_valid_or_return_new_tokens(access_token)
        )
        if validation_result:
            user_id = await TokenService.get_user_id_by_token(access_token)
            query = select(Post).filter(Post.id == post_id, Post.author_id == user_id)
            result = await db_session.execute(query)
            post = result.one_or_none()
            if not post:
                raise HTTPException(
                    status_code=404,
                    detail="Запись не найдена либо удалить запись может только автор."
                )
            post_table = Post.__table__
            delete_query = (delete(post_table).
                            where(post_table.c.id == uuid.UUID(post_id)))
            await db_session.execute(delete_query)
            await db_session.commit()
            content = {'id': post_id}
            headers = {
                'X-Access-Token': validation_result[0],
                'X-Refresh-Token': validation_result[1]
            } if isinstance(validation_result, tuple) else {}
            return JSONResponse(content=content, headers=headers)

    @staticmethod
    async def like_post(
        post_id: str,
        authorization: Annotated[str, Header()],
        db_session: AsyncSession,
        cache: client.Redis
    ) -> str:
        user_id = await PostService.check_user_allowed_like_or_dislike(post_id, authorization, db_session)
        if user_id:
            if await PostService.check_user_likes_or_dislikes_first_time(user_id, post_id, cache, 'like'):
                like_count = await PostService.get_post_like_count(post_id, cache)
                like_count += 1
                await cache.set(f'like:{post_id}', like_count)
                await cache.rpush(f'like:{user_id}', post_id)
                await cache.lrem(f'dislike:{user_id}', 0, post_id)
                return 'Лайк добавлен.'
            
    @staticmethod
    async def dislike_post(
        post_id: str,
        authorization: Annotated[str, Header()],
        db_session: AsyncSession,
        cache: client.Redis
    ) -> str:
        user_id = await PostService.check_user_allowed_like_or_dislike(post_id, authorization, db_session)
        if user_id:
            if await PostService.check_user_likes_or_dislikes_first_time(user_id, post_id, cache, 'dislike'):
                dislike_count = await PostService.get_post_dislike_count(post_id, cache)
                dislike_count += 1
                await cache.set(f'dislike:{post_id}', dislike_count)
                await cache.rpush(f'dislike:{user_id}', post_id)
                await cache.lrem(f'like:{user_id}', 0, post_id)
                return 'Дизлайк добавлен.'
        
    @staticmethod
    async def get_post_like_count(post_id: str, cache: client.Redis) -> int:
        like_key = f'like:{post_id}'
        like_count: bytes = await cache.get(like_key)
        if not like_count:
            await cache.set(like_key, 0)
            return 0
        return int(like_count.decode())
    
    @staticmethod
    async def get_post_dislike_count(post_id: str, cache: client.Redis) -> int:
        dislike_key = f'dislike:{post_id}'
        dislike_count: bytes = await cache.get(dislike_key)
        if not dislike_count:
            await cache.set(dislike_key, 0)
            return 0
        return int(dislike_count.decode())
    
    @staticmethod
    async def check_user_allowed_like_or_dislike(
        post_id: str,
        authorization: Annotated[str, Header()],
        db_session: AsyncSession
    ) -> str:
        access_token = await TokenService.get_token_authorization(authorization)
        validation_result = (
            await TokenService.check_access_token_valid_or_return_new_tokens(access_token)
        )
        if validation_result:
            user_id = await TokenService.get_user_id_by_token(access_token)
            query = select(Post).filter(Post.id == post_id, Post.author_id == user_id)
            result = await db_session.execute(query)
            post = result.one_or_none()
            if post:
                raise HTTPException(
                    status_code=403, detail="Действие запрещено."
                )
            return user_id
    
    @staticmethod
    async def check_user_likes_or_dislikes_first_time(
        user_id: str, post_id: str, cache: client.Redis, flag: str
    ) -> bool:
        if not await cache.exists(f'{flag}:{user_id}'):
            return True
        posts_user_liked = await cache.lrange(f'{flag}:{user_id}', 0, -1)
        if post_id.encode() in posts_user_liked:
            raise HTTPException(
                status_code=403, detail="Действие запрещено."
            )
        return True
