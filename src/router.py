from fastapi import Response
from fastapi import APIRouter, Depends
from src.schemas import TokenRequest, TokenResponse, UserDB, UserRegistration, UserLogin
from src.schemas import PostDB
from sqlalchemy.ext.asyncio import AsyncSession

from databases import get_db_session
from src.service import PostService, UserService
from utils import TokenService


user_router = APIRouter()

post_router = APIRouter()


@user_router.post('/registration', status_code=201)
async def register_user(
    user: UserRegistration, db_session: AsyncSession = Depends(get_db_session)
) -> Response:
    response = await UserService.create_user(user, db_session)
    return response


@user_router.post('/login', status_code=200)
async def login_user(
    user: UserLogin
) -> Response:
    response = await UserService.login_user(user)
    return response


@user_router.post(
        '/{user_id}/refresh-token',
        response_model=TokenResponse,
        status_code=201
)
async def refresh_tokens(user_id: str, token_request: TokenRequest) -> TokenResponse:
    access_token, refresh_roken = await TokenService.refresh_tokens(
        user_id, token_request.refresh_token
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_roken
    )


@post_router.get('/posts')
async def posts():
    pass


@post_router.post('/posts', response_model=PostDB, status_code=201)
async def create_post(
    user: UserDB, post: PostDB, db_session: AsyncSession = Depends(get_db_session)
) -> PostDB:
    response = await PostService.create_and_publish_post(user, post, db_session)
    return response


@post_router.patch('/posts/<post_id>')
async def update_post():
    pass


@post_router.delete('/posts/<post_id>')
async def delete_post():
    pass
