from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- PostgreSQL ---
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "postgres"   # matches docker-compose service name
    POSTGRES_PORT: str = "5432"

    # --- JWT ---
    SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CricAPI ---
    CRIC_API_KEY: str = ""

    # --- App ---
    APP_ENV: str = "development"      # "development" or "production"
    ALLOWED_ORIGINS: str = "http://localhost"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """
    Cached so the .env file is only read once per process.
    Use as a FastAPI dependency: settings = Depends(get_settings)
    Or import directly:          from app.config import get_settings; settings = get_settings()
    """
    return Settings()