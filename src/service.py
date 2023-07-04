from fastapi import HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from src.schemas import UserLogin, UserRegistration
from src.models import User
from databases import get_db_session


class UserService:


    @staticmethod
    async def create_user(user: UserRegistration) -> Response:
        if (not await UserService.check_login_exists(user.login)
            and not await UserService.check_email_exists(user.email)):
            success_text = await UserService._save_user_to_database(user)
            return Response(content=success_text, status_code=201)

    @staticmethod
    async def check_login_exists(login: str) -> bool:
        async for session in get_db_session():
            query = select(User.login).filter(User.login == login)
            result = await session.execute(query)
            if result.scalar_one():
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
                if result.scalar_one():
                    raise HTTPException(
                        status_code=400,
                        detail='Пользователь с таким email уже зарегистрирован.'
                    )
            return False
    
    @staticmethod
    async def save_user_to_database(user: UserRegistration) -> str:
        hashed_password = generate_password_hash(user.password)
        new_user = User(
            login=user.login,
            hashed_password=hashed_password,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email
        )
        async for session in get_db_session():
            session.add(new_user)
            await session.commit()
        return "Вы успешно зарегистрировались."
    