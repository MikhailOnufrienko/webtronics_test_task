from datetime import datetime, timedelta
from typing import Annotated

from fastapi import HTTPException, Header
from fastapi.exceptions import RequestValidationError
from jose import jwt
from redis.asyncio import client

from config import settings
from databases import get_redis


class TokenService:

    @staticmethod
    async def generate_tokens(user_id: str) -> tuple[str]:
        subject_id = {'sub': user_id}
        access_token = await TokenService.generate_access_token(
            subject_id, settings.ACCESS_TOKEN_EXPIRES_IN
        )
        refresh_token = await TokenService.generate_refresh_token(
            subject_id, settings.REFRESH_TOKEN_EXPIRES_IN
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

    @staticmethod
    async def refresh_tokens(
        user_id: str, old_access_token: str, old_refresh_token: str
    ) -> tuple[str, str]:
        cache: client.Redis = await get_redis()
        if await TokenService.check_old_token_equal_stored_token(
            user_id, old_refresh_token, cache
        ):
            new_access_token, new_refresh_token = await TokenService.generate_tokens(
                user_id
            )
            await TokenService.save_new_refresh_token_to_cache(
                user_id, new_refresh_token, cache
            )
            await TokenService.add_invalid_access_token_to_cache(
                user_id, old_access_token, cache
            )
            return new_access_token, new_refresh_token

    @staticmethod
    async def check_old_token_equal_stored_token(
        user_id: str, old_token: str, cache: client.Redis
    ) -> bool:
        stored_token: bytes = await cache.get(user_id)
        if not stored_token or stored_token.decode() != old_token:
            raise HTTPException(status_code=400, detail="Недействительный refresh-токен.")
        return True
    
    @staticmethod
    async def save_new_refresh_token_to_cache(
        user_id: str, token: str, cache: client.Redis
    ) -> None:
        expires: int = settings.REFRESH_TOKEN_EXPIRES_IN * 60 * 60 * 24 # in seconds
        await cache.setex(user_id, expires, token)

    @staticmethod
    async def add_invalid_access_token_to_cache(
        access_token: str, cache: client.Redis
    ) -> None:
        current_datetime = datetime.now()
        invalid_token_key = f'invalid:{current_datetime}'
        expires: int = settings.ACCESS_TOKEN_EXPIRES_IN * 60 * 60 * 24 # in seconds
        await cache.setex(invalid_token_key, expires, access_token)

    @staticmethod
    async def check_access_token_valid(access_token: str) -> bool:
        if await TokenService.check_access_token_signature_valid(access_token) and \
            await TokenService.check_access_token_not_expired(access_token):
            return True

    @staticmethod
    async def check_access_token_signature_valid(access_token: str) -> bool:
        header, payload, signature = access_token.split('.')
        subject = await TokenService.get_user_id_by_token(access_token)
        if signature == jwt.decode(
            access_token,
            settings.ACCESS_JWT_SECRET_KEY,
            settings.JWT_ALGORITHM,
            subject=subject):
            return True

    @staticmethod
    async def get_user_id_by_token(access_token: str) -> str:
        claims = jwt.get_unverified_claims(access_token)
        return claims['sub']
    
    @staticmethod
    async def check_access_token_not_expired(access_token: str) -> bool:
        cache: client.Redis = await get_redis()
        cursor, keys = await cache.scan(b'0', match='*')
        for key in keys:
            value = await cache.get(key)
            if value == access_token.encode():
                raise HTTPException(
                    status_code=400,
                    detail='Просроченный access-token. Требуется аутентификация.'
                )
        return True
    
    @staticmethod
    async def get_token_authorization(authorization: Annotated[str, Header()]) -> str:
        scheme, token = authorization.split()
        print("scheme: ", scheme)
        if scheme.lower() != 'bearer':
            raise HTTPException(status_code=401, detail="Недействительная схема авторизации.")
        return token