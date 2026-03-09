from functools import lru_cache
from pathlib import Path

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
    session_cookie_name: str = Field(default="agentmobile_session", alias="SESSION_COOKIE_NAME")
    csrf_cookie_name: str = Field(default="agentmobile_csrf", alias="CSRF_COOKIE_NAME")
    session_ttl_hours: int = Field(default=168, alias="SESSION_TTL_HOURS")
    allowed_hosts: tuple[str, ...] = Field(default=("*",), alias="ALLOWED_HOSTS")
    ws_allowed_origins: tuple[str, ...] = Field(default=tuple(), alias="WS_ALLOWED_ORIGINS")
    enable_public_registration: bool = Field(default=False, alias="ENABLE_PUBLIC_REGISTRATION")
    codex_turn_timeout_seconds: int = Field(default=300, alias="CODEX_TURN_TIMEOUT_SECONDS")
    heartbeat_poll_interval_seconds: int = Field(default=15, alias="HEARTBEAT_POLL_INTERVAL_SECONDS")
    heartbeat_claim_batch_size: int = Field(default=5, alias="HEARTBEAT_CLAIM_BATCH_SIZE")
    heartbeat_min_interval_minutes: int = Field(default=5, alias="HEARTBEAT_MIN_INTERVAL_MINUTES")
    heartbeat_interval_presets: tuple[int, ...] = Field(
        default=(5, 15, 30, 60),
        alias="HEARTBEAT_INTERVAL_PRESETS",
    )
    heartbeat_run_stale_after_seconds: int = Field(
        default=900,
        alias="HEARTBEAT_RUN_STALE_AFTER_SECONDS",
    )
    heartbeat_allowed_base_path: str | None = Field(default=None, alias="HEARTBEAT_ALLOWED_BASE_PATH")
    codex_runtime_target: str = Field(default="container", alias="CODEX_RUNTIME_TARGET")
    codex_host_workspace_path: str | None = Field(default=None, alias="CODEX_HOST_WORKSPACE_PATH")
    codex_host_codex_bin: str = Field(default="/usr/bin/codex", alias="CODEX_HOST_CODEX_BIN")
    codex_host_pid: int = Field(default=1, alias="CODEX_HOST_PID")
    codex_workspace_path: str = Field(default="/workspace", alias="CODEX_WORKSPACE_PATH")
    uploads_path: str = Field(default="./uploads", alias="UPLOADS_PATH")
    admin_bootstrap_email: str | None = Field(default=None, alias="ADMIN_BOOTSTRAP_EMAIL")
    admin_bootstrap_password: str | None = Field(default=None, alias="ADMIN_BOOTSTRAP_PASSWORD")
    admin_bootstrap_password_hash: str | None = Field(default=None, alias="ADMIN_BOOTSTRAP_PASSWORD_HASH")
    # Backward-compatible aliases for earlier bootstrap naming.
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

    @field_validator("codex_turn_timeout_seconds")
    @classmethod
    def validate_codex_turn_timeout_seconds(cls, value: int) -> int:
        if value < 1:
            raise ValueError("CODEX_TURN_TIMEOUT_SECONDS must be >= 1")
        return value

    @field_validator("heartbeat_poll_interval_seconds")
    @classmethod
    def validate_heartbeat_poll_interval_seconds(cls, value: int) -> int:
        if value < 1:
            raise ValueError("HEARTBEAT_POLL_INTERVAL_SECONDS must be >= 1")
        return value

    @field_validator("heartbeat_claim_batch_size")
    @classmethod
    def validate_heartbeat_claim_batch_size(cls, value: int) -> int:
        if value < 1:
            raise ValueError("HEARTBEAT_CLAIM_BATCH_SIZE must be >= 1")
        return value

    @field_validator("heartbeat_min_interval_minutes")
    @classmethod
    def validate_heartbeat_min_interval_minutes(cls, value: int) -> int:
        if value < 1:
            raise ValueError("HEARTBEAT_MIN_INTERVAL_MINUTES must be >= 1")
        return value

    @field_validator("heartbeat_interval_presets", mode="before")
    @classmethod
    def validate_heartbeat_interval_presets(cls, value: tuple[int, ...] | list[int] | str) -> tuple[int, ...]:
        if isinstance(value, str):
            parts = [item.strip() for item in value.split(",") if item.strip()]
            try:
                parsed = tuple(int(item) for item in parts)
            except ValueError as exc:
                raise ValueError("HEARTBEAT_INTERVAL_PRESETS must contain integer minutes") from exc
            return parsed

        if isinstance(value, (tuple, list)):
            parsed = tuple(int(item) for item in value)
            return parsed

        raise ValueError("HEARTBEAT_INTERVAL_PRESETS must be a comma-separated list or int tuple")

    @field_validator("heartbeat_run_stale_after_seconds")
    @classmethod
    def validate_heartbeat_run_stale_after_seconds(cls, value: int) -> int:
        if value < 1:
            raise ValueError("HEARTBEAT_RUN_STALE_AFTER_SECONDS must be >= 1")
        return value

    @field_validator("heartbeat_allowed_base_path")
    @classmethod
    def validate_heartbeat_allowed_base_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("codex_runtime_target")
    @classmethod
    def validate_codex_runtime_target(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"container", "host"}
        if normalized not in allowed:
            raise ValueError(f"CODEX_RUNTIME_TARGET must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("codex_host_workspace_path")
    @classmethod
    def validate_codex_host_workspace_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("codex_host_codex_bin")
    @classmethod
    def validate_codex_host_codex_bin(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("CODEX_HOST_CODEX_BIN cannot be empty")
        if not Path(normalized).is_absolute():
            raise ValueError("CODEX_HOST_CODEX_BIN must be an absolute path")
        return normalized

    @field_validator("codex_host_pid")
    @classmethod
    def validate_codex_host_pid(cls, value: int) -> int:
        if value < 1:
            raise ValueError("CODEX_HOST_PID must be >= 1")
        return value

    @field_validator("uploads_path")
    @classmethod
    def validate_uploads_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("UPLOADS_PATH cannot be empty")
        return normalized

    @field_validator("codex_workspace_path")
    @classmethod
    def validate_codex_workspace_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("CODEX_WORKSPACE_PATH cannot be empty")
        return normalized

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def validate_allowed_hosts(cls, value: tuple[str, ...] | list[str] | str) -> tuple[str, ...]:
        if isinstance(value, str):
            parts = [item.strip().lower() for item in value.split(",") if item.strip()]
            return tuple(parts or ["*"])

        if isinstance(value, (tuple, list)):
            normalized = [str(item).strip().lower() for item in value if str(item).strip()]
            return tuple(normalized or ["*"])

        raise ValueError("ALLOWED_HOSTS must be a comma-separated list or string tuple")

    @field_validator("ws_allowed_origins", mode="before")
    @classmethod
    def validate_ws_allowed_origins(
        cls,
        value: tuple[str, ...] | list[str] | str,
    ) -> tuple[str, ...]:
        if isinstance(value, str):
            parts = [item.strip().lower() for item in value.split(",") if item.strip()]
            return tuple(parts)

        if isinstance(value, (tuple, list)):
            normalized = [str(item).strip().lower() for item in value if str(item).strip()]
            return tuple(normalized)

        raise ValueError("WS_ALLOWED_ORIGINS must be a comma-separated list or string tuple")

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
