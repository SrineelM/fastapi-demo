"""
Core Configuration Module

This module handles application configuration using Pydantic Settings.
It supports environment variables and .env files for configuration management.

Features:
- Environment-based settings (development/staging/production)
- Type-safe configuration using Pydantic
- RS256 (RSA) and HS256 JWT support
- Database abstraction with SQLAlchemy
- Security configuration (rate limiting, file uploads, CORS)
- Observability (OpenTelemetry, Prometheus, structured logging)
- Per-environment .env files support

Usage:
    from app.core.config import get_settings
    
    settings = get_settings()
    print(settings.APP_NAME)
    print(settings.is_production())
"""

import os
import json
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    Application settings class using Pydantic.
    
    Supports three environments:
    - development: Loose security, debugging enabled, in-memory DB
    - staging: Production-like, testing enabled, real DB
    - production: Strict security, no debugging, hardened deployment
    
    Configuration is loaded from:
    1. .env.{ENVIRONMENT} file (e.g., .env.production)
    2. .env file (fallback)
    3. Environment variables
    4. Default values
    """
    
    # ==================== APPLICATION ====================
    APP_NAME: str = Field(default="FastAPI Comprehensive Guide")
    APP_VERSION: str = Field(default="1.0.0")
    ENVIRONMENT: str = Field(default="development", validation_alias="ENV")
    DEBUG: bool = Field(default=True)
    
    # ==================== SERVER ====================
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    WORKERS: int = Field(default=4)
    RELOAD: bool = Field(default=True)
    
    # ==================== CORS ====================
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:4200"]
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(default=["*"], description="Allowed HTTP methods")
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"], description="Allowed HTTP headers")
    
    # Redis Configuration
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    CACHE_TTL: int = Field(default=300, description="Cache TTL in seconds")
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./test.db",
        description="Database connection URL"
    )
    DB_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")
    
    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT expiration time")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, description="Rate limit per minute")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json/text)")
    
    # Observability
    ENABLE_METRICS: bool = Field(default=True, description="Enable Prometheus metrics")
    ENABLE_TRACING: bool = Field(default=True, description="Enable distributed tracing")
    JAEGER_HOST: str = Field(default="localhost", description="Jaeger host")
    JAEGER_PORT: int = Field(default=6831, description="Jaeger port")
    
    # Performance
    MAX_CONCURRENT_REQUESTS: int = Field(default=100, description="Max concurrent requests")
    REQUEST_TIMEOUT: int = Field(default=30, description="Request timeout in seconds")
    
    # AWS Configuration
    AWS_REGION: str = Field(default="us-east-1", description="AWS region")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, description="AWS access key")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, description="AWS secret key")
    
    # Kubernetes Configuration
    K8S_NAMESPACE: str = Field(default="default", description="Kubernetes namespace")
    K8S_SERVICE_NAME: str = Field(default="fastapi-guide", description="Kubernetes service name")
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./fastapi_dev.db"
    )
    DB_POOL_SIZE: int = Field(default=5)
    DB_MAX_OVERFLOW: int = Field(default=10)
    DB_ECHO: bool = Field(default=False)
    
    # Security - JWT
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production"
    )
    ALGORITHM: str = Field(default="HS256")
    PRIVATE_KEY_PATH: str = Field(default="keys/private.pem")
    PUBLIC_KEY_PATH: str = Field(default="keys/public.pem")
    KEY_ROTATION_DAYS: int = Field(default=90)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    CLOCK_SKEW_TOLERANCE_SECONDS: int = Field(default=10)
    
    # Password Requirements
    PASSWORD_MIN_LENGTH: int = Field(default=8)
    PASSWORD_REQUIRE_UPPERCASE: bool = Field(default=True)
    PASSWORD_REQUIRE_LOWERCASE: bool = Field(default=True)
    PASSWORD_REQUIRE_DIGITS: bool = Field(default=True)
    PASSWORD_REQUIRE_SPECIAL: bool = Field(default=True)
    
    # Token Blacklist
    TOKEN_BLACKLIST_ENABLED: bool = Field(default=True)
    REDIS_BLACKLIST_TTL: int = Field(default=86400)
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_REQUESTS: int = Field(default=100)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60)
    AUTH_RATE_LIMIT_REQUESTS: int = Field(default=5)
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = Field(default=300)
    UPLOAD_RATE_LIMIT_REQUESTS: int = Field(default=10)
    UPLOAD_RATE_LIMIT_WINDOW_SECONDS: int = Field(default=300)
    
    # File Uploads
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024)
    UPLOAD_DIR: str = Field(default="uploads")
    ALLOWED_FILE_EXTENSIONS: List[str] = Field(
        default=[".txt", ".pdf", ".jpg", ".jpeg", ".png", ".csv", ".json"]
    )
    MAX_REQUEST_SIZE: int = Field(default=100 * 1024 * 1024)
    
    # Security Headers
    ENABLE_SECURITY_HEADERS: bool = Field(default=True)
    HSTS_MAX_AGE: int = Field(default=31536000)
    
    # Caching
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    CACHE_TTL: int = Field(default=300)
    ENABLE_ETAG: bool = Field(default=True)
    
    # Observability
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")
    ENABLE_STRUCTURED_LOGGING: bool = Field(default=True)
    ENABLE_OTEL: bool = Field(default=False)
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(
        default="http://localhost:4317"
    )
    OTEL_ENABLED_INSTRUMENTATIONS: List[str] = Field(
        default=["fastapi", "sqlalchemy", "requests"]
    )
    PROMETHEUS_ENABLED: bool = Field(default=False)
    PROMETHEUS_METRICS_PORT: int = Field(default=8001)
    ENABLE_REQUEST_ID_LOGGING: bool = Field(default=True)
    TRACE_SAMPLING_RATE: float = Field(default=0.1)
    
    # Deployment
    WORKER_CLASS: str = Field(default="uvicorn.workers.UvicornWorker")
    AWS_REGION: str = Field(default="us-east-1")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None)
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None)
    CONTAINER_REGISTRY: str = Field(default="docker.io")
    
    # Model configuration for Pydantic v2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
        json_file=None
    )
    
    # ==================== VALIDATORS ====================
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            # Handle comma-separated values
            if v.startswith('['):
                # Try parsing as JSON if it looks like JSON
                import json
                try:
                    return json.loads(v)
                except:
                    pass
            # Parse as comma-separated
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return v
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v
    
    @field_validator("ALGORITHM")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm."""
        allowed = ["HS256", "RS256"]
        if v not in allowed:
            raise ValueError(f"ALGORITHM must be one of {allowed}")
        return v
    
    # ==================== HELPER METHODS ====================
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"
    
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.ENVIRONMENT == "staging"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"
    
    def use_rsa_keys(self) -> bool:
        """Check if RSA keys should be used (RS256)."""
        return self.ALGORITHM == "RS256" or self.is_production()
    
    def get_database_url(self) -> str:
        """Get database URL with environment-specific defaults."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.is_production():
            raise ValueError("DATABASE_URL must be set in production")
        return "sqlite+aiosqlite:///./fastapi_dev.db"


# ==================== SETTINGS LOADING ====================

def get_settings() -> Settings:
    """Load settings based on environment."""
    env = os.getenv("ENV", "development")
    env_file = f".env.{env}"
    try:
        if os.path.exists(env_file):
            return Settings(_env_file=env_file)
        return Settings()
    except Exception as e:
        # If loading fails, create with all defaults
        return Settings()


@lru_cache()
def get_cached_settings() -> Settings:
    """Get cached settings instance."""
    return get_settings()


# Backward compatibility
try:
    settings = get_cached_settings()
except Exception:
    # If loading fails, create with all defaults
    settings = Settings()

