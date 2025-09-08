from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl
from typing import List

class Settings(BaseSettings):
    APP_ENV: str = "dev"
    APP_SECRET: str

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    DATABASE_URL: str
    REDIS_URL: str

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    BT_CLIENT: str = "qb"
    QB_URL: AnyHttpUrl
    QB_USER: str
    QB_PASS: str

    ALLOWED_SAVE_DIRS: str = "/downloads,/music"
    DEFAULT_SAVE_DIR: str = "/downloads"

    CORS_ORIGINS: str = "*"

    class Config:
        env_file = "./deploy/env/api.env"
        extra = "ignore"

settings = Settings()  # type: ignore
