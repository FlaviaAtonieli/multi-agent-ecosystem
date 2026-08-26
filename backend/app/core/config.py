from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
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

    # LLM foundation. Disabled by default so the project boots without an API key;
    # once enabled, OpenRouter is the primary Model Gateway (no mock provider).
    llm_enabled: bool = False
    llm_provider: Literal["openai", "openrouter"] = "openrouter"
    llm_model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    llm_allowed_models: str = "nvidia/nemotron-3-super-120b-a12b:free"
    llm_timeout_seconds: int = 45
    llm_max_output_tokens: int = 1200
    llm_max_input_chars: int = 12000
    llm_requests_per_hour_technician: int = 20

    # Privacy-safe defaults.
    llm_store_provider_response: bool = False
    llm_store_result_content: bool = False
    llm_log_content: bool = False
    llm_redact_sensitive_data: bool = True

    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"

    # OpenRouter is the primary Model Gateway: a single credential exposes many
    # providers/models (e.g. "openai/gpt-5-mini", "anthropic/claude-sonnet-4.5"),
    # useful to compare models without recoding the LLM abstraction.
    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_app_url: str = "http://localhost:5173"

    # Retrieval-augmented generation. Independent from llm_enabled: retrieval can
    # run (and be tested) even while the model call itself stays mocked/disabled.
    rag_enabled: bool = True
    rag_top_k: int = 3
    rag_chunk_max_chars: int = 800
    rag_chunk_overlap: int = 100

    # Real MCP transport used to invoke Agent Skills. "stdio" spawns each skill's
    # server as a genuine subprocess (JSON-RPC over stdio); "memory" connects to
    # the same MCPServer object in-process (fast, used by the test suite).
    mcp_skill_transport: Literal["memory", "stdio"] = "stdio"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [item.strip() for item in self.trusted_hosts.split(",") if item.strip()]

    @property
    def llm_allowed_model_list(self) -> list[str]:
        return [item.strip() for item in self.llm_allowed_models.split(",") if item.strip()]

    @property
    def openai_api_key_value(self) -> str | None:
        if self.openai_api_key is None:
            return None
        value = self.openai_api_key.get_secret_value().strip()
        return value or None

    @property
    def openrouter_api_key_value(self) -> str | None:
        if self.openrouter_api_key is None:
            return None
        value = self.openrouter_api_key.get_secret_value().strip()
        return value or None

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @model_validator(mode="after")
    def validate_llm_configuration(self) -> "Settings":
        if self.llm_max_input_chars < 1000:
            raise ValueError("LLM_MAX_INPUT_CHARS deve ser maior ou igual a 1000.")
        if self.llm_max_output_tokens < 128:
            raise ValueError("LLM_MAX_OUTPUT_TOKENS deve ser maior ou igual a 128.")
        if self.llm_requests_per_hour_technician < 1:
            raise ValueError("LLM_REQUESTS_PER_HOUR_TECHNICIAN deve ser maior que zero.")

        if not self.llm_enabled:
            return self

        if self.llm_model not in self.llm_allowed_model_list:
            raise ValueError(
                f"O modelo '{self.llm_model}' não está em LLM_ALLOWED_MODELS."
            )

        if self.llm_provider == "openai" and not self.openai_api_key_value:
            raise ValueError(
                "OPENAI_API_KEY é obrigatória quando LLM_ENABLED=true e LLM_PROVIDER=openai."
            )

        if self.llm_provider == "openrouter" and not self.openrouter_api_key_value:
            raise ValueError(
                "OPENROUTER_API_KEY é obrigatória quando LLM_ENABLED=true e LLM_PROVIDER=openrouter."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
