from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://ops_user:ops_password@localhost:5432/ops_under_pressure"
    JWT_SECRET: str = "newtonite-ops-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    STALE_HOURS: int = 24
    UNOWNED_HOURS: int = 4
    STUCK_APPROVAL_HOURS: int = 8
    OUTBOX_MAX_ATTEMPTS: int = 5
    OUTBOX_POLL_INTERVAL: float = 1.0
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
