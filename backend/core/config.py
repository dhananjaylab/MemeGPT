import os
from typing import List
from pydantic import ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings


# Placeholder values that must never survive into a production deployment.
# Used by the post-init validator below to fail fast at startup instead of
# silently running with a guessable secret / pointing at nowhere.
_UNSAFE_DEFAULT_SECRET_KEY = "your-secret-key-here"
_UNSAFE_DEFAULT_DATABASE_MARKER = "user:password@localhost"


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost/memegpt"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    arq_redis_settings: str = Field(default="", alias="ARQ_REDIS_SETTINGS")
    arq_queue_name: str = Field(default="arq:queue", alias="ARQ_QUEUE_NAME")
    
    # Google Gemini
    gemini_api_key: str = ""
    ai_provider: str = Field(default="gemini", alias="AI_PROVIDER")  # "gemini" preferred; "anthropic" is an automatic fallback, not user-selectable

    # Google OAuth
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")

    # Anthropic — Phase 2: actually wired up as a Gemini fallback now (see
    # services/meme_ai.py). The key was configured in every .env file from
    # day one but never used by any code path.
    anthropic_api_key: str = ""
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", alias="ANTHROPIC_MODEL")

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

    # Observability — Phase 2: these were referenced in every .env* file
    # and sentry-sdk/structlog were declared dependencies, but nothing ever
    # called sentry_sdk.init() or configured structlog. See core/sentry.py
    # and core/logging.py.
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    sentry_traces_sample_rate: float = Field(default=0.1, alias="SENTRY_TRACES_SAMPLE_RATE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Content moderation — Phase 2: gates is_public on generated memes.
    # See services/moderation.py for the full rationale.
    moderation_enabled: bool = Field(default=True, alias="MODERATION_ENABLED")
    # Fail-OPEN by default: if the moderation provider itself is down,
    # generation still succeeds (just unreviewed) rather than taking down
    # 100% of generation on a moderation-provider outage. Flip to True once
    # you've measured how often that actually happens for your traffic.
    moderation_fail_closed: bool = Field(default=False, alias="MODERATION_FAIL_CLOSED")
    
    # Frontend
    frontend_url: str = "http://localhost:3000"
    
    # Security
    secret_key: str = _UNSAFE_DEFAULT_SECRET_KEY
    allowed_hosts_raw: str = Field(default="localhost,127.0.0.1,0.0.0.0,testserver", alias="ALLOWED_HOSTS")

    # JWT / session lifetimes.
    # Access tokens are intentionally short-lived; the refresh token (issued
    # as an httpOnly cookie, see services/auth.py) is what keeps the user
    # signed in without ever putting a long-lived credential in localStorage.
    jwt_access_token_expire_minutes: int = Field(default=60, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    refresh_cookie_name: str = Field(default="refresh_token", alias="REFRESH_COOKIE_NAME")

    # Generation burst limiting — short-window guard applied in addition to
    # the existing daily quota, specifically on /api/memes/generate*.
    generation_burst_limit: int = Field(default=5, alias="GENERATION_BURST_LIMIT")
    generation_burst_window_seconds: int = Field(default=60, alias="GENERATION_BURST_WINDOW_SECONDS")

    # CORS Configuration
    cors_origins_raw: str = Field(default="http://localhost:3000,http://127.0.0.1:3000", alias="CORS_ORIGINS")
    cors_allow_credentials: bool = True
    cors_allow_methods_raw: str = Field(default="GET,POST,PUT,PATCH,DELETE,OPTIONS", alias="CORS_ALLOW_METHODS")
    cors_allow_headers_raw: str = Field(default="Authorization,Content-Type,X-API-Key,X-Requested-With,Accept,Origin,User-Agent", alias="CORS_ALLOW_HEADERS")
    cors_max_age: int = 600
    
    # Environment detection
    environment: str = "development"
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    # Rate limiting
    rate_limit_free: int = 5
    rate_limit_pro: int = 500
    rate_limit_api: int = 500
    rate_limit_templates_read: int = 1000
    rate_limit_trending_read: int = 1000
    
    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_api: str = ""
    
    # Cloudflare R2
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "memegpt-images"
    r2_public_url: str = ""

    @property
    def r2_endpoint_url(self) -> str:
        if not self.r2_account_id:
            return ""
        return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"

    @property
    def r2_access_key(self) -> str:
        return self.r2_access_key_id

    @property
    def r2_secret_key(self) -> str:
        return self.r2_secret_access_key

    @property
    def arq_redis_url(self) -> str:
        return self.arq_redis_settings or self.redis_url

    model_config = ConfigDict(
        env_file=".env",
        extra="ignore"
    )
    
    @property
    def allowed_hosts(self) -> List[str]:
        return self._parse_comma_separated(self.allowed_hosts_raw)
    
    @property
    def cors_origins(self) -> List[str]:
        return self._parse_comma_separated(self.cors_origins_raw)
    
    @property
    def cors_allow_methods(self) -> List[str]:
        return self._parse_comma_separated(self.cors_allow_methods_raw)
    
    @property
    def cors_allow_headers(self) -> List[str]:
        return self._parse_comma_separated(self.cors_allow_headers_raw)
    
    def _parse_comma_separated(self, value: str) -> List[str]:
        """Parse comma-separated string into list, handling empty values"""
        if not value or not value.strip():
            return []
        return [item.strip() for item in value.split(",") if item.strip()]
    
    @property
    def has_gemini(self) -> bool:
        """Check if Gemini API key is configured"""
        return bool(self.gemini_api_key)

    # ── Phase 1 security remediation ──────────────────────────────────────
    # Fail fast at startup rather than silently serving production traffic
    # with a guessable JWT secret or a placeholder database connection.
    # This previously had no enforcement at all.
    @model_validator(mode="after")
    def _reject_unsafe_production_defaults(self) -> "Settings":
        if not self.is_production:
            return self

        problems: List[str] = []

        if self.secret_key == _UNSAFE_DEFAULT_SECRET_KEY or len(self.secret_key) < 32:
            problems.append(
                "SECRET_KEY is missing, default, or too short (need >= 32 chars) "
                "while ENVIRONMENT=production."
            )

        if _UNSAFE_DEFAULT_DATABASE_MARKER in self.database_url:
            problems.append(
                "DATABASE_URL still points at the localhost/placeholder default "
                "while ENVIRONMENT=production."
            )

        if problems:
            raise ValueError(
                "Refusing to start in production with unsafe configuration:\n  - "
                + "\n  - ".join(problems)
                + "\nSet these via real environment variables before deploying."
            )

        return self


settings = Settings()
