import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from redis.asyncio import Redis

from app.api.vacancy import api_v1_router as vacancy_api_v1_router
from app.api.resume import api_v1_router as resume_api_v1_router
from app.core.config import settings
from app.db.session import async_session_maker
from app.messaging.outbox_dispatcher import OutboxDispatcher
from app.messaging.redis_publisher import RedisPublisher


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = Redis.from_url(settings.REDIS_URL)
    app.state.redis = redis
    publisher = RedisPublisher(redis, settings.REDIS_QUEUE_NAME)
    dispatcher = OutboxDispatcher(async_session_maker, publisher)
    dispatch_task = asyncio.create_task(dispatcher.run())
    try:
        yield
    finally:
        dispatch_task.cancel()
        with suppress(asyncio.CancelledError):
            await dispatch_task
        await redis.aclose()


app = FastAPI(lifespan=lifespan)

app.include_router(vacancy_api_v1_router)
app.include_router(resume_api_v1_router)


@app.get("/health")
def health():
    return {"health": "OK"}
