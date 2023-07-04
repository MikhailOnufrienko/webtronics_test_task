from datetime import datetime, timedelta

from jose import jwt
from redis.asyncio import client

from src.schemas import UserLogin
from config import settings
from databases import get_redis


class TokenService:


    @staticmethod
    async def generate_tokens(user: UserLogin) -> tuple[str]:
        username = {'sub': user.login}
        access_token = await TokenService.generate_access_token(
            username, settings.ACCESS_TOKEN_EXPIRES_IN
        )
        refresh_token = await TokenService.generate_refresh_token(
            username, settings.REFRESH_TOKEN_EXPIRES_IN
        )
        return access_token, refresh_token
    
    @staticmethod
    async def generate_access_token(data: dict, expires_delta: int) -> str:
        to_encode = await TokenService.prepare_data_for_generating_tokens(
            data, expires_delta
        )
        encoded_jwt = jwt.encode(
            to_encode, settings.ACCESS_JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    async def generate_refresh_token(data: dict, expires_delta: int) -> str:
        to_encode = await TokenService.prepare_data_for_generating_tokens(
            data, expires_delta
        )
        encoded_jwt = jwt.encode(
            to_encode, settings.REFRESH_JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    async def prepare_data_for_generating_tokens(
        data: dict, expires_delta: int
    ) -> dict:
        to_encode = data.copy()
        expire_in_days = datetime.utcnow() + timedelta(days=expires_delta)
        to_encode.update({'exp': expire_in_days})
        return to_encode
    
    @staticmethod
    async def save_refresh_token_to_cache(user_id: str, token: str) -> None:
        cache: client.Redis = await get_redis()
        if await TokenService.check_refresh_token_exists_in_cache(cache, user_id):
            await TokenService.delete_refresh_token_from_cache(cache, user_id)
        expires: int = settings.REFRESH_TOKEN_EXPIRES_IN * 60 * 60 * 24 # in seconds
        await cache.setex(user_id, expires, token)

    @staticmethod
    async def check_refresh_token_exists_in_cache(
        cache: client.Redis, user_id: str
    ) -> bool:
        old_token = await cache.get(user_id)
        if old_token:
            return True
        return False

    @staticmethod
    async def delete_refresh_token_from_cache(
        cache: client.Redis, user_id: str
    ) -> None:
        cache.delete(user_id)
