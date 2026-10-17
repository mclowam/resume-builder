from os import getenv


class Config:
    WORKER_API_TOKEN: str | None = getenv("WORKER_API_TOKEN")

    REDIS_URL: str = getenv("REDIS_URL", "redis://localhost:16379/0")
    REDIS_QUEUE_NAME: str = getenv("REDIS_QUEUE_NAME", "embedding_tasks")

    RESUME_API_URL: str = getenv("RESUME_API_URL", "http://localhost:8002")
    HTTP_TIME_OUT: float = 20.0

    OPENAI_API_KEY: str | None = getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL: str = getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    EMBEDDING_MODEL: str = getenv("EMBEDDING_MODEL", "text-embedding-3-small")


settings = Config()
