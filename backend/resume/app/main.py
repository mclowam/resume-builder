from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.api.vacancy import api_v1_router as vacancy_api_v1_router
from app.api.resume import api_v1_router as resume_api_v1_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = Redis.from_url(settings.REDIS_URL)
    app.state.redis = redis
    try:
        yield
    finally:
        await redis.aclose()


app = FastAPI(lifespan=lifespan)

app.include_router(vacancy_api_v1_router)
app.include_router(resume_api_v1_router)


@app.get("/health")
def health():
    return {"health": "OK"}
