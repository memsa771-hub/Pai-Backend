from functools import lru_cache
from typing import Annotated, Any, Literal, Self
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
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
    enable_api_docs: bool = Field(default=True, alias="ENABLE_API_DOCS")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"], alias="CORS_ORIGINS"
    )
    trusted_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["*"],
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
    frontend_onboarding_path: str = Field(default="/onboarding", alias="FRONTEND_ONBOARDING_PATH")
    frontend_home_path: str = Field(default="/", alias="FRONTEND_HOME_PATH")

    auth_http_timeout_seconds: float = Field(default=10.0, alias="AUTH_HTTP_TIMEOUT_SECONDS")

    database_url: str = Field(..., alias="DATABASE_URL")
    database_ssl_verify: bool = Field(default=True, alias="DATABASE_SSL_VERIFY")
    vault_encryption_key: str = Field(..., alias="VAULT_ENCRYPTION_KEY")

    llm_default_provider: str = Field(default="openai", alias="LLM_DEFAULT_PROVIDER")
    llm_counseling_model: str = Field(default="gpt-5.6-terra", alias="LLM_COUNSELING_MODEL")
    llm_extraction_model: str = Field(default="gpt-5.6-luna", alias="LLM_EXTRACTION_MODEL")
    llm_document_model: str = Field(default="gpt-5.6-luna", alias="LLM_DOCUMENT_MODEL")
    llm_document_vision_model: str = Field(default="gpt-4o-mini", alias="LLM_DOCUMENT_VISION_MODEL")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="https://api.deepseek.com/v1", alias="DEEPSEEK_BASE_URL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    llm_timeout_seconds: float = Field(default=60.0, alias="LLM_TIMEOUT_SECONDS")
    llm_counseling_max_tokens: int = Field(default=2048, alias="LLM_COUNSELING_MAX_TOKENS")

    llm_simple_counseling_model: str = Field(default="gpt-5.6-luna", alias="LLM_SIMPLE_COUNSELING_MODEL")
    llm_goal_model: str = Field(default="gpt-5.6-terra", alias="LLM_GOAL_MODEL")
    llm_complex_model: str = Field(default="gpt-5.6-sol", alias="LLM_COMPLEX_MODEL")
    llm_counseling_reasoning: str = Field(default="low", alias="LLM_COUNSELING_REASONING")
    llm_extraction_reasoning: str = Field(default="none", alias="LLM_EXTRACTION_REASONING")
    llm_goal_reasoning: str = Field(default="medium", alias="LLM_GOAL_REASONING")
    llm_counseling_timeout_seconds: float = Field(default=30, alias="LLM_COUNSELING_TIMEOUT_SECONDS")
    enable_integrated_goal_analysis: bool = Field(default=False, alias="ENABLE_INTEGRATED_GOAL_ANALYSIS")
    enable_goal_escalation: bool = Field(default=True, alias="ENABLE_GOAL_ESCALATION")
    # Embedded workers are a development opt-in. Production uses dedicated processes.
    run_workers_in_api: bool = Field(default=False, alias="RUN_WORKERS_IN_API")

    supabase_storage_bucket: str = Field(default="documents", alias="SUPABASE_STORAGE_BUCKET")
    document_max_bytes: int = Field(default=10_485_760, alias="DOCUMENT_MAX_BYTES")
    document_processing_timeout_seconds: float = Field(
        default=180.0, alias="DOCUMENT_PROCESSING_TIMEOUT_SECONDS"
    )
    document_allow_image_uploads: bool = Field(default=True, alias="DOCUMENT_ALLOW_IMAGE_UPLOADS")
    document_ocr_provider: str = Field(default="openai_vision", alias="DOCUMENT_OCR_PROVIDER")
    document_vision_max_pages: int = Field(default=20, alias="DOCUMENT_VISION_MAX_PAGES")
    document_vision_batch_pages: int = Field(default=2, alias="DOCUMENT_VISION_BATCH_PAGES")
    document_vision_max_tokens: int = Field(default=8000, alias="DOCUMENT_VISION_MAX_TOKENS")
    document_malware_scan_provider: str = Field(default="none", alias="DOCUMENT_MALWARE_SCAN_PROVIDER")
    chat_recent_message_limit: int = Field(default=8, alias="CHAT_RECENT_MESSAGE_LIMIT")
    enable_document_worker: bool = Field(default=True, alias="ENABLE_DOCUMENT_WORKER")
    # One loop per API process. person_id advisory locks keep students serialized
    # if you run `uvicorn --workers N`.
    enable_intelligence_worker: bool = Field(default=True, alias="ENABLE_INTELLIGENCE_WORKER")
    enable_goal_worker: bool = Field(default=True, alias="ENABLE_GOAL_WORKER")

    # Web search (Tavily) — leave empty until you add the key; tool degrades gracefully
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    tavily_max_results: int = Field(default=5, alias="TAVILY_MAX_RESULTS")
    tavily_search_depth: str = Field(default="basic", alias="TAVILY_SEARCH_DEPTH")

    # AgentSpan semantic / conversation memory
    semantic_memory_max_results: int = Field(default=5, alias="SEMANTIC_MEMORY_MAX_RESULTS")
    conversation_memory_max_messages: int = Field(
        default=40, alias="CONVERSATION_MEMORY_MAX_MESSAGES"
    )
    enable_counselor_tools: bool = Field(default=True, alias="ENABLE_COUNSELOR_TOOLS")
    counselor_max_tool_rounds: int = Field(default=1, alias="COUNSELOR_MAX_TOOL_ROUNDS")
    # Cap rows scanned when ranking lexically (the vector path ranks in SQL)
    semantic_memory_scan_limit: int = Field(default=200, alias="SEMANTIC_MEMORY_SCAN_LIMIT")
    # Semantic recall via embeddings. Off (or no API key) -> lexical ranking, unchanged.
    enable_semantic_embeddings: bool = Field(default=True, alias="ENABLE_SEMANTIC_EMBEDDINGS")
    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    # Must match the model's output size and the vector(N) column in migration 014.
    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")
    # Rows pulled by vector search before structural re-ranking in Python.
    embedding_candidate_limit: int = Field(default=40, alias="EMBEDDING_CANDIDATE_LIMIT")
    # Read and write embed on different deadlines because they sit in different
    # places. A read blocks the student's reply; a write runs after the reply is
    # already sent, so it can afford to wait rather than leave a row unembedded.
    #
    # Measured: text-embedding-3-small answers in ~1.8s from ap-southeast-2,
    # occasionally 8s. At 0.6s every call timed out and recall silently fell
    # back to lexical ranking, which looks like working software. Latency is
    # regional, so this is a knob — but the default must let a normal call
    # finish, not merely bound the wait. 8s covers the measured tail; trimming
    # it toward "typical" would cut off exactly the slow-but-fine calls.
    embedding_read_timeout_seconds: float = Field(
        default=8.0, gt=0, alias="EMBEDDING_READ_TIMEOUT_SECONDS"
    )
    # Writes embed a batch of rows in one request, after the transaction has
    # committed and after the student has their reply. A failure costs only a
    # retry — the rows keep embedding=NULL and the next turn (or
    # scripts/backfill_memory_embeddings.py) picks them up — so this deadline
    # can be generous where the read deadline cannot.
    embedding_write_timeout_seconds: float = Field(
        default=15.0, gt=0, alias="EMBEDDING_WRITE_TIMEOUT_SECONDS"
    )
    # Deprecated: set the two above instead. Kept so an existing .env keeps
    # starting — when set it seeds whichever of the two was left at default.
    embedding_timeout_seconds: float | None = Field(
        default=None, gt=0, alias="EMBEDDING_TIMEOUT_SECONDS"
    )
    # Must exceed embedding_read_timeout_seconds: recall embeds the query first,
    # so a budget below it can never succeed. The margin covers the pgvector
    # search and ranking that follow the embedding. No le= ceiling — a
    # deployment far from the provider has to be able to raise this.
    memory_recall_budget_seconds: float = Field(default=10.0, gt=0, alias="MEMORY_RECALL_BUDGET_SECONDS")
    # Consecutive embedding failures before recall stops calling the provider.
    # During an outage every turn otherwise pays the full read timeout before
    # falling back to lexical; the student feels that as a stalled counselor.
    embedding_breaker_threshold: int = Field(
        default=3, ge=1, alias="EMBEDDING_BREAKER_THRESHOLD"
    )
    # How long recall stays lexical before one turn probes the provider again.
    embedding_breaker_cooldown_seconds: float = Field(
        default=60.0, gt=0, alias="EMBEDDING_BREAKER_COOLDOWN_SECONDS"
    )
    turn_understanding_budget_seconds: float = Field(default=2.0, gt=0, le=3, alias="TURN_UNDERSTANDING_BUDGET_SECONDS")
    memory_rerank_url: str = Field(default="", alias="MEMORY_RERANK_URL")
    memory_rerank_api_key: str = Field(default="", alias="MEMORY_RERANK_API_KEY")
    memory_rerank_model: str = Field(default="", alias="MEMORY_RERANK_MODEL")
    memory_rerank_budget_seconds: float = Field(default=0.2, gt=0, le=1, alias="MEMORY_RERANK_BUDGET_SECONDS")
    # Postgres LangGraph checkpoints add remote writes per node — off by default for chat latency
    enable_graph_checkpoint: bool = Field(default=False, alias="ENABLE_GRAPH_CHECKPOINT")

    enable_rate_limits: bool = Field(default=True, alias="ENABLE_RATE_LIMITS")
    rate_limit_fail_closed: bool = Field(default=False, alias="RATE_LIMIT_FAIL_CLOSED")
    # consume() runs a clock read plus an upsert per counter and commits, which
    # measures ~1.7s steady against a pooled remote database. At 1.0s it never
    # completed, so limits were not enforced. Keep a five-second ceiling because
    # this work runs before every request and the configured policy fails open.
    rate_limit_backend_timeout_seconds: float = Field(
        default=2.5, gt=0, le=5, alias="RATE_LIMIT_BACKEND_TIMEOUT_SECONDS"
    )
    request_limit_per_minute: int = Field(default=120, gt=0, alias="REQUEST_LIMIT_PER_MINUTE")
    user_request_limit_per_minute: int = Field(default=60, gt=0, alias="USER_REQUEST_LIMIT_PER_MINUTE")
    upload_limit_per_day: int = Field(default=30, gt=0, alias="UPLOAD_LIMIT_PER_DAY")
    llm_call_limit_per_day: int = Field(default=300, gt=0, alias="LLM_CALL_LIMIT_PER_DAY")
    llm_token_limit_per_day: int = Field(default=1000000, gt=0, alias="LLM_TOKEN_LIMIT_PER_DAY")
    llm_global_token_limit_per_day: int = Field(default=10000000, gt=0, alias="LLM_GLOBAL_TOKEN_LIMIT_PER_DAY")
    readiness_timeout_seconds: float = Field(default=3, gt=0, alias="READINESS_TIMEOUT_SECONDS")
    worker_heartbeat_max_age_seconds: int = Field(default=600, gt=0, alias="WORKER_HEARTBEAT_MAX_AGE_SECONDS")
    worker_queue_max_age_seconds: int = Field(default=900, gt=0, alias="WORKER_QUEUE_MAX_AGE_SECONDS")

    @field_validator(
        "supabase_anon_key",
        "supabase_service_role_key",
        "supabase_jwt_secret",
        "supabase_url",
        "database_url",
        "vault_encryption_key",
        "deepseek_api_key",
        "openai_api_key",
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

    @field_validator(
        "email_verification_redirect_url",
        "password_reset_redirect_url",
        mode="before",
    )
    @classmethod
    def frontend_redirect_url(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        url = value.strip()
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Redirect URL must be an absolute http(s) frontend address.")
        if not parsed.path or parsed.path == "/":
            raise ValueError(
                "Redirect URL must include a dedicated path "
                "(e.g. /auth/verify-email or /auth/reset-password), not the site root."
            )
        return url

    @model_validator(mode="after")
    def redirects_match_cors(self) -> Self:
        allowed = set(self.cors_origins)
        if "*" in allowed:
            return self
        for url in (self.email_verification_redirect_url, self.password_reset_redirect_url):
            parsed = urlparse(url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            if origin not in allowed:
                raise ValueError(
                    f"Redirect origin {origin} must also be listed in CORS_ORIGINS."
                )
        return self

    # A round trip to an embeddings API does not finish in under a second from
    # most regions — measured at ~2s, occasionally 8s, from ap-southeast-2. Any
    # budget below this is not "tight", it is off, and the failure is swallowed.
    _MIN_VIABLE_EMBEDDING_TIMEOUT = 1.5
    # consume() is several statements plus a commit against a pooled remote
    # Postgres; measured ~1.7s steady from the same region.
    _MIN_VIABLE_RATE_LIMIT_TIMEOUT = 2.0

    # Which of the two new timeouts the caller actually supplied. Captured
    # before validation because that is the only point where "absent" is still
    # distinguishable; consulted after, because that is the only point where
    # the value cannot still be overwritten. See the validators below.
    _legacy_embedding_seed: dict[str, float] = {}

    @model_validator(mode="before")
    @classmethod
    def _capture_legacy_embedding_timeout(cls, data: Any) -> Any:
        """Record what EMBEDDING_TIMEOUT_SECONDS should seed, if anything.

        The single knob became two. A deployment that tuned the old one to
        survive its distance from the provider must not silently revert to the
        default on upgrade, so the old value seeds whichever of the two was not
        supplied. Setting a specific one always wins.

        Deciding that here is unavoidable: once validation finishes, every
        field is populated and an omitted timeout is indistinguishable from a
        supplied one. model_fields_set does not close the gap either, because
        model_dump() emits *all* fields, so a round-trip
        (`Settings.model_validate(other.model_dump())`) marks the read timeout
        as explicitly set. Only the raw input says what the caller passed.

        Applying it here does not work, though: pydantic-settings merges its
        own sources (environment, .env) *after* this runs, so a value in .env —
        `.env.example` ships one — silently overwrites whatever is written
        here. Hence the split: decide now, apply in the after-validator.
        """
        if not isinstance(data, dict):
            return data
        legacy = cls._lookup(data, "embedding_timeout_seconds", "EMBEDDING_TIMEOUT_SECONDS")
        if legacy is None:
            cls._legacy_embedding_seed = {}
            return data
        try:
            legacy = float(legacy)
        except (TypeError, ValueError):
            # Not a number: leave it for normal field validation to reject.
            cls._legacy_embedding_seed = {}
            return data
        write_default = cls.model_fields["embedding_write_timeout_seconds"].default
        seed: dict[str, float] = {}
        if not cls._caller_supplied(data, "embedding_read_timeout_seconds"):
            seed["embedding_read_timeout_seconds"] = legacy
        if not cls._caller_supplied(data, "embedding_write_timeout_seconds"):
            # The old knob bounded a read; a write that inherits it keeps at
            # least the write default rather than being tightened by it.
            seed["embedding_write_timeout_seconds"] = max(legacy, write_default)
        cls._legacy_embedding_seed = seed
        return data

    @staticmethod
    def _caller_supplied(data: dict, name: str) -> bool:
        """Whether the field was set deliberately, ignoring .env boilerplate.

        Three origins have to be told apart, because only the third is weak
        enough to be overridden by the legacy knob:

        * the field NAME — a caller passing a dict, or a model_dump
          round-trip. Always deliberate.
        * a real process environment variable under the ALIAS. Deliberate: an
          operator exported it for this run.
        * the same ALIAS coming from the `.env` file, which `.env.example`
          ships pre-filled with the defaults. Not a statement of intent, so a
          deployment that still tunes only EMBEDDING_TIMEOUT_SECONDS is not
          overruled by boilerplate it never edited.
        """
        import os

        if data.get(name) is not None:
            return True
        alias = Settings.model_fields[name].alias
        return bool(alias) and os.environ.get(alias) is not None

    @model_validator(mode="after")
    def _apply_legacy_embedding_timeout(self) -> Self:
        """Apply the seed decided before validation, after the sources merged.

        Ordered before embedding_budgets_are_reachable so the reachability
        check sees the timeouts that will actually be used.
        """
        seed = type(self)._legacy_embedding_seed
        if not seed:
            return self
        type(self)._legacy_embedding_seed = {}
        for name, value in seed.items():
            object.__setattr__(self, name, value)
        return self

    @staticmethod
    def _lookup(data: dict, name: str, alias: str) -> Any:
        """A field's raw input value, by field name or by alias.

        Input reaches here by field name (a model_dump round-trip) or by alias
        (environment and .env), so both have to be checked.
        """
        for key in (name, alias):
            if key in data and data[key] is not None:
                return data[key]
        return None

    @model_validator(mode="after")
    def embedding_budgets_are_reachable(self) -> Self:
        """Refuse timeouts that can never succeed.

        Both failures here are caught and turned into "no memory found", so a
        too-small budget looks exactly like a student the counselor knows
        nothing about. Fail at startup instead: silently downgrading the memory
        the counselor runs on is worse than not starting.
        """
        if not self.enable_semantic_embeddings:
            return self
        for alias, value in (
            ("EMBEDDING_READ_TIMEOUT_SECONDS", self.embedding_read_timeout_seconds),
            ("EMBEDDING_WRITE_TIMEOUT_SECONDS", self.embedding_write_timeout_seconds),
        ):
            if value < self._MIN_VIABLE_EMBEDDING_TIMEOUT:
                raise ValueError(
                    f"{alias} ({value}s) is below "
                    f"{self._MIN_VIABLE_EMBEDDING_TIMEOUT}s, which no embeddings round trip "
                    "meets — every call would time out and recall would silently fall back to "
                    "keyword matching. Raise it, or set ENABLE_SEMANTIC_EMBEDDINGS=false to "
                    "choose lexical recall deliberately."
                )
        # Recall embeds the query before it can search, so the budget has to
        # outlast the call it contains.
        if self.memory_recall_budget_seconds <= self.embedding_read_timeout_seconds:
            raise ValueError(
                f"MEMORY_RECALL_BUDGET_SECONDS ({self.memory_recall_budget_seconds}s) must "
                f"exceed EMBEDDING_READ_TIMEOUT_SECONDS "
                f"({self.embedding_read_timeout_seconds}s), or the budget kills the "
                "embedding it is waiting for."
            )
        return self

    @model_validator(mode="after")
    def rate_limit_timeout_is_reachable(self) -> Self:
        """A limiter that always times out is a limiter that is switched off.

        consume() fails open by default, so an unreachable budget does not break
        requests — it silently stops enforcing every limit, including the daily
        LLM spend caps, while the logs show a handled warning.
        """
        if (
            self.enable_rate_limits
            and self.rate_limit_backend_timeout_seconds < self._MIN_VIABLE_RATE_LIMIT_TIMEOUT
        ):
            raise ValueError(
                f"RATE_LIMIT_BACKEND_TIMEOUT_SECONDS "
                f"({self.rate_limit_backend_timeout_seconds}s) is below "
                f"{self._MIN_VIABLE_RATE_LIMIT_TIMEOUT}s, which the counter upsert cannot "
                "meet against a remote database — the limiter would fail open on every "
                "request and enforce nothing. Raise it, or set ENABLE_RATE_LIMITS=false "
                "to disable limits deliberately."
            )
        return self

    def next_path(self, *, onboarding_completed: bool) -> str:
        return self.frontend_home_path if onboarding_completed else self.frontend_onboarding_path

    @property
    def supabase_auth_base(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
