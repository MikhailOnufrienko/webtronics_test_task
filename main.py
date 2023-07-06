import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import ORJSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError

from config import settings
from databases import get_db_session, get_redis
from src.router import user_router, post_router


app = FastAPI(
    title=settings.SERVICE_NAME,
    docs_url='/api/openapi',
    openapi_url='/api/openapi.json',
    default_response_class=ORJSONResponse)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"pydantic error": exc.errors()},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.on_event('startup')
async def startup() -> None:
    global redis, postgres
    redis = await get_redis()
    async for session in get_db_session():
        postgres = session


@app.on_event('shutdown')
async def shutdown() -> None:
    await redis.close()
    await postgres.close()


app.include_router(user_router, prefix='/api/v1/auth/user', tags=['user'])
app.include_router(post_router, prefix='/api/v1', tags=['post'])


if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host='127.0.0.1',
        port=8001, 
        reload=True
    )
