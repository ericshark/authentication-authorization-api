from typing import Literal

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    DATABASE_URL: str
    SECRET_KEY: str
    AUTH_STRATEGY: Literal["JWT", "SESSION"]
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    is_production: bool
    REFRESH_TOKENS_ENABLED: bool


settings = Settings()
