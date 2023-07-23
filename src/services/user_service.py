from fastapi import HTTPException
from redis import client
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from werkzeug.security import generate_password_hash, check_password_hash

from src.schemas import Token, UserLogin, UserRegistration
from src.models import User
from src.services.token_service import TokenService


class UserService:

    @staticmethod
    async def create_user(user: UserRegistration, db_session: AsyncSession) -> str:
        if (not await UserService.check_login_exists(user.login, db_session)
            and not await UserService.check_email_exists(user.email, db_session)):
            success = await UserService.save_user_to_database(user, db_session)
            return success

    @staticmethod
    async def check_login_exists(login: str, db_session: AsyncSession) -> bool:
            query = select(User.login).filter(User.login == login)
            result = await db_session.execute(query)
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail='Пользователь с таким логином уже зарегистрирован.'
                )
            return False
        
    @staticmethod
    async def check_email_exists(email: str, db_session: AsyncSession) -> bool:
            query = select(User.email).filter(User.email == email)
            result = await db_session.execute(query)
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail='Пользователь с таким email уже зарегистрирован.'
                )
            return False
    
    @staticmethod
    async def save_user_to_database(
        user: UserRegistration, db_session: AsyncSession
    ) -> str:
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
    async def login_user(user: UserLogin, db_session: AsyncSession, cache: client.Redis) -> tuple:
        if await UserService.check_credentials_correct(user.login, user.password, db_session):
            user_id = await UserService.get_user_id_by_login(user, db_session)
            access_token, refresh_token = await TokenService.generate_tokens(user_id)
            await TokenService.save_refresh_token_to_cache(user_id, refresh_token, cache)
            success = "Вы успешно вошли в свою учётную запись."
            headers = {
                'X-Access-Token': access_token,
                'X-Refresh-Token': refresh_token
            }
            return success, headers
    
    @staticmethod
    async def check_credentials_correct(login: str, password: str, db_session: AsyncSession) -> bool:
        query_for_login = select(User.login).filter(User.login == login)
        result = await db_session.execute(query_for_login)
        if result.scalar_one_or_none():
            query_for_password = select(
                User.hashed_password
            ).filter(User.login == login)
            result = await db_session.execute(query_for_password)
            hashed_password = result.scalar_one()
            if check_password_hash(hashed_password, password):
                return True
        raise HTTPException(status_code=401, detail='Логин или пароль не верен.')
        
    @staticmethod
    async def get_user_id_by_login(user: UserLogin, db_session: AsyncSession) -> str:
        query = select(User.id).filter(User.login == user.login)
        result = await db_session.execute(query)
        user_id = result.scalar_one()
        return str(user_id)
        
    @staticmethod
    async def logout_user(tokens: Token, cache: client.Redis) -> str:
        await TokenService.add_invalid_access_token_to_cache(tokens.access_token, cache)
        user_id = await TokenService.get_user_id_by_token(tokens.access_token)
        await TokenService.delete_refresh_token_from_cache(cache, user_id)
        return 'Вы успешно вышли из учётной записи.'
