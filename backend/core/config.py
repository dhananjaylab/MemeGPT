import os
from typing import List
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost/memegpt"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    arq_queue_name: str = Field(default="arq:queue", alias="ARQ_QUEUE_NAME")
    
    # OpenAI
    openai_api_key: str = ""
    
    # Google Gemini
    gemini_api_key: str = ""
    ai_provider: str = Field(default="openai", alias="AI_PROVIDER")  # "openai", "gemini", or "both"
    
    # Imgflip API
    imgflip_username: str = ""
    imgflip_password: str = ""
    
    # Frontend
    frontend_url: str = "http://localhost:3000"
    
    # Security
    secret_key: str = "your-secret-key-here"
    allowed_hosts_raw: str = Field(default="localhost,127.0.0.1,0.0.0.0,testserver", alias="ALLOWED_HOSTS")
    
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
    
    @property
    def has_openai(self) -> bool:
        """Check if OpenAI API key is configured"""
        return bool(self.openai_api_key)


settings = Settings()