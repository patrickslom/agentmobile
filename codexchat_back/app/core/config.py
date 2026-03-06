from functools import lru_cache

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    app_env: str = Field(default="production", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_pretty: bool = Field(default=False, alias="LOG_PRETTY")
    api_port: int = Field(default=8000, alias="API_PORT")
    worker_port: int = Field(default=8001, alias="WORKER_PORT")
    session_secret: str = Field(alias="SESSION_SECRET")
    session_cookie_name: str = Field(default="codexchat_session", alias="SESSION_COOKIE_NAME")
    csrf_cookie_name: str = Field(default="codexchat_csrf", alias="CSRF_COOKIE_NAME")
    session_ttl_hours: int = Field(default=168, alias="SESSION_TTL_HOURS")
    admin_email: str | None = Field(default=None, alias="ADMIN_EMAIL")
    admin_password: str | None = Field(default=None, alias="ADMIN_PASSWORD")
    admin_password_hash: str | None = Field(default=None, alias="ADMIN_PASSWORD_HASH")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value:
            raise ValueError("DATABASE_URL is required")

        if not value.startswith("postgresql"):
            raise ValueError("DATABASE_URL must use a PostgreSQL driver URL")

        return value

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"development", "staging", "production", "test"}
        if normalized not in allowed:
            raise ValueError(f"APP_ENV must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("session_secret")
    @classmethod
    def validate_session_secret(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 32:
            raise ValueError("SESSION_SECRET must be at least 32 characters long")
        return normalized

    @field_validator("session_ttl_hours")
    @classmethod
    def validate_session_ttl_hours(cls, value: int) -> int:
        if value < 1:
            raise ValueError("SESSION_TTL_HOURS must be >= 1")
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(allowed))}")
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
