import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost/memegpt"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # OpenAI
    openai_api_key: str = ""
    
    # Frontend
    frontend_url: str = "http://localhost:3000"
    
    # Security
    secret_key: str = "your-secret-key-here"
    allowed_hosts: List[str] = ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]
    
    # CORS Configuration
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    cors_allow_headers: List[str] = ["Authorization", "Content-Type", "X-API-Key", "X-Requested-With", "Accept", "Origin", "User-Agent"]
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

    class Config:
        env_file = ".env"
        extra = "ignore" # Ignore extra env vars


settings = Settings()