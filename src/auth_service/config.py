from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"], alias="CORS_ORIGINS"
    )
    trusted_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1"],
        alias="TRUSTED_HOSTS",
    )

    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")
    cookie_same_site: Literal["lax", "strict", "none"] = Field(
        default="lax", alias="COOKIE_SAME_SITE"
    )
    refresh_cookie_name: str = Field(default="pai_refresh_token", alias="REFRESH_COOKIE_NAME")
    csrf_cookie_name: str = Field(default="pai_csrf_token", alias="CSRF_COOKIE_NAME")

    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_anon_key: str = Field(..., alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(..., alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_jwt_secret: str = Field(..., alias="SUPABASE_JWT_SECRET")
    supabase_jwt_audience: str = Field(default="authenticated", alias="SUPABASE_JWT_AUDIENCE")

    email_verification_redirect_url: str = Field(..., alias="EMAIL_VERIFICATION_REDIRECT_URL")
    password_reset_redirect_url: str = Field(..., alias="PASSWORD_RESET_REDIRECT_URL")

    auth_http_timeout_seconds: float = Field(default=10.0, alias="AUTH_HTTP_TIMEOUT_SECONDS")

    database_url: str = Field(..., alias="DATABASE_URL")
    database_ssl_verify: bool = Field(default=True, alias="DATABASE_SSL_VERIFY")
    vault_encryption_key: str = Field(..., alias="VAULT_ENCRYPTION_KEY")

    llm_default_provider: str = Field(default="deepseek", alias="LLM_DEFAULT_PROVIDER")
    llm_counseling_model: str = Field(default="deepseek-chat", alias="LLM_COUNSELING_MODEL")
    llm_extraction_model: str = Field(default="deepseek-chat", alias="LLM_EXTRACTION_MODEL")
    llm_document_model: str = Field(default="deepseek-chat", alias="LLM_DOCUMENT_MODEL")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="https://api.deepseek.com/v1", alias="DEEPSEEK_BASE_URL")
    llm_timeout_seconds: float = Field(default=60.0, alias="LLM_TIMEOUT_SECONDS")

    supabase_storage_bucket: str = Field(default="documents", alias="SUPABASE_STORAGE_BUCKET")
    document_max_bytes: int = Field(default=10_485_760, alias="DOCUMENT_MAX_BYTES")
    document_processing_timeout_seconds: float = Field(
        default=120.0, alias="DOCUMENT_PROCESSING_TIMEOUT_SECONDS"
    )
    chat_recent_message_limit: int = Field(default=20, alias="CHAT_RECENT_MESSAGE_LIMIT")
    enable_document_worker: bool = Field(default=True, alias="ENABLE_DOCUMENT_WORKER")

    # Web search (Tavily) — leave empty until you add the key; tool degrades gracefully
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    tavily_max_results: int = Field(default=5, alias="TAVILY_MAX_RESULTS")
    tavily_search_depth: str = Field(default="basic", alias="TAVILY_SEARCH_DEPTH")

    # AgentSpan semantic / conversation memory
    semantic_memory_max_results: int = Field(default=5, alias="SEMANTIC_MEMORY_MAX_RESULTS")
    conversation_memory_max_messages: int = Field(
        default=40, alias="CONVERSATION_MEMORY_MAX_MESSAGES"
    )
    enable_counselor_tools: bool = Field(default=False, alias="ENABLE_COUNSELOR_TOOLS")
    counselor_max_tool_rounds: int = Field(default=2, alias="COUNSELOR_MAX_TOOL_ROUNDS")
    # Cap rows scanned for lexical semantic ranking until pgvector is wired
    semantic_memory_scan_limit: int = Field(default=200, alias="SEMANTIC_MEMORY_SCAN_LIMIT")
    # Postgres LangGraph checkpoints add remote writes per node — off by default for chat latency
    enable_graph_checkpoint: bool = Field(default=False, alias="ENABLE_GRAPH_CHECKPOINT")

    @field_validator(
        "supabase_anon_key",
        "supabase_service_role_key",
        "supabase_jwt_secret",
        "supabase_url",
        "database_url",
        "vault_encryption_key",
        "deepseek_api_key",
        "tavily_api_key",
        mode="before",
    )
    @classmethod
    def strip_secrets(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("cors_origins", "trusted_hosts", mode="before")
    @classmethod
    def split_csv(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def supabase_auth_base(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
