from os import getenv


class Config:
    WORKER_API_TOKEN: str | None = getenv("WORKER_API_TOKEN")

    DB_HOST: str = getenv("DB_HOST", "localhost")
    DB_PORT: str = getenv("DB_PORT", "5434")
    DB_NAME: str = getenv("DB_NAME", "resume_db")
    DB_USER: str = getenv("DB_USER", "admin")
    DB_PASSWORD: str = getenv("DB_PASSWORD", "admin")

    MINIO_ENDPOINT_URL: str = getenv("MINIO_ENDPOINT_URL", "http://localhost:9000")
    MINIO_ROOT_USER: str = getenv("MINIO_ROOT_USER", "minioadmin")
    MINIO_ROOT_PASSWORD: str = getenv("MINIO_ROOT_PASSWORD", "minioadmin")
    MINIO_BUCKET: str = getenv("MINIO_BUCKET", "resumes")

    REDIS_URL: str = getenv("REDIS_URL", "redis://localhost:16379/0")
    REDIS_QUEUE_NAME: str = getenv("REDIS_QUEUE_NAME", "embedding_tasks")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Config()
