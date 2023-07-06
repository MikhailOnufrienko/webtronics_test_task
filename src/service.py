import json

from fastapi import HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from jose import jwt
from werkzeug.security import generate_password_hash, check_password_hash

from src.schemas import UserLogin, UserRegistration
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
            user_id = await UserService.get_user_id(user)
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
        try:
            query_for_login = select(User.login).filter(User.login == login)
            async for session in get_db_session():
                result = await session.execute(query_for_login)
                if result.scalar_one_or_none():
                    query_for_password = select(
                        User.hashed_password
                    ).filter(User.login == login)
                    result = await session.execute(query_for_password)
                    hashed_password = result.scalar_one()
                    if check_password_hash(hashed_password, password):
                        return True
        except HTTPException:
            raise HTTPException(status_code=401, detail='Логин или пароль не верен.')
        
    @staticmethod
    async def get_user_id(user: UserLogin) -> str:
        query = select(User.id).filter(User.login == user.login)
        async for session in get_db_session():
            result = await session.execute(query)
            return str(result.scalar_one())


class PostService:

    @staticmethod
    async def create_and_publish_post(
        post: PostBase, db_session: AsyncSession
    ) -> PostDB:
        if await TokenService.check_access_token_not_expired(post.access_token):
            author_id = await PostService.get_author_id(post.access_token)
            new_post = Post(
                title=post.title,
                content=post.content,
                author_id=author_id
            )
            db_session.add(new_post)
            await db_session.commit()
            new_post_id_as_str = str(new_post.id)
            return PostDB(
                id=new_post_id_as_str,
                title=new_post.title,
                author_id=new_post.author_id,
                creation_dt=new_post.creation_dt
            )

    @staticmethod
    async def get_author_id(access_token: str) -> str:
        try:
            decoded_jwt: dict = jwt.decode(
                access_token, settings.ACCESS_JWT_SECRET_KEY, settings.JWT_ALGORITHM
            )
            return decoded_jwt['sub']
        except:
            raise HTTPException(
                status_code=400,
                detail='Невалидный access-токен. Требуется аутентификация.'
            )

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
