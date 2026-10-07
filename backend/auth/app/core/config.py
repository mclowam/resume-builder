from os import getenv


class Config:
    DB_HOST: str = getenv("DB_HOST", "localhost")
    DB_PORT: str = getenv("DB_PORT", "5433")
    DB_NAME: str = getenv("DB_NAME", "auth_db")
    DB_USER: str = getenv("DB_USER", "admin")
    DB_PASSWORD: str = getenv("DB_PASSWORD", "admin")

    SECRET_KEY: str = getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_EXPIRE_MIN: int = 15
    REFRESH_EXPIRE_DAYS: int = 30

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

settings = Config()