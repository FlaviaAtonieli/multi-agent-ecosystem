from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AgentHub"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"

    database_url: str = "sqlite:///./agenthub.db"
    auto_create_tables: bool = True

    cors_origins: str = "http://localhost:5173"
    trusted_hosts: str = "localhost,127.0.0.1"

    session_cookie_name: str = "agenthub_session"
    csrf_cookie_name: str = "agenthub_csrf"
    cookie_secure: bool = False
    session_ttl_hours: int = 8
    max_active_sessions: int = 5

    login_max_attempts: int = 5
    lockout_minutes: int = 15
    allow_registration: bool = True

    bootstrap_admin_name: str | None = None
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [item.strip() for item in self.trusted_hosts.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
