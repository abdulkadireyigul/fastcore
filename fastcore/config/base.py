"""
Base configuration module for FastAPI applications.

This module provides the base settings class that other settings classes inherit from.
It handles basic application configuration like app name, debug mode, and version.
"""

import secrets
from typing import List, Optional

from pydantic import ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings

# from src.logging import ensure_logger

# logger = ensure_logger(None, __name__, None)


class BaseAppSettings(BaseSettings):
    """
    Base settings class for application configuration.

    This class provides the foundation for all environment-specific settings classes.
    It includes basic settings that are common across all environments.

    Attributes:
        APP_NAME: The name of the application
        DEBUG: Flag to enable/disable debug mode
        VERSION: Application version string
        CACHE_URL: Redis connection URL for caching
        CACHE_DEFAULT_TTL: Default cache TTL in seconds
        CACHE_KEY_PREFIX: Optional prefix for cache keys
        DATABASE_URL: Database connection URL
        DB_ECHO: Enable SQL query logging (echo)
        DB_POOL_SIZE: Connection pool size for the database
        JWT_SECRET_KEY: Secret key for JWT token signing
        JWT_ALGORITHM: Algorithm used for JWT token signing
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES: Expiration time for access tokens in minutes
        JWT_REFRESH_TOKEN_EXPIRE_DAYS: Expiration time for refresh tokens in days
        JWT_AUDIENCE: Audience claim for JWT tokens
        JWT_ISSUER: Issuer claim for JWT tokens
        JWT_ALLOWED_AUDIENCES: List of allowed audience values for token validation
        MIDDLEWARE_CORS_OPTIONS: CORS middleware options (passed to CORSMiddleware)
        RATE_LIMITING_OPTIONS: Rate limiting options (max_requests, window_seconds)
        RATE_LIMITING_BACKEND: Rate limiting backend: "memory" or "redis"
        HEALTH_PATH: Health check endpoint path
        HEALTH_INCLUDE_DETAILS: Include detailed health check info in response
        METRICS_PATH: Prometheus metrics endpoint path
        METRICS_EXCLUDE_PATHS: List of paths to exclude from metrics collection
    """

    APP_NAME: str = Field(default="FastCore")
    DEBUG: bool = Field(default=False)
    VERSION: str = Field(default="0.1.0")

    # Cache configuration
    CACHE_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching",
    )
    CACHE_DEFAULT_TTL: int = Field(
        default=300, description="Default cache TTL in seconds"
    )
    CACHE_KEY_PREFIX: str = Field(
        default="", description="Optional prefix for cache keys"
    )

    # Database configuration
    DATABASE_URL: str = Field(default=None, description="Database connection URL")
    DB_ECHO: bool = Field(default=False, description="Enable SQL query logging (echo)")
    DB_POOL_SIZE: int = Field(
        default=5, description="Connection pool size for the database"
    )

    # Security configuration
    JWT_SECRET_KEY: str = Field(
        default="",  # Empty default to encourage explicit setting
        description="Secret key for signing JWT tokens",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256", description="Algorithm used for JWT token signing"
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Expiration time for access tokens in minutes"
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, description="Expiration time for refresh tokens in days"
    )
    JWT_AUDIENCE: Optional[str] = Field(
        default=None, description="Audience claim for JWT tokens"
    )
    JWT_ISSUER: Optional[str] = Field(
        default=None, description="Issuer claim for JWT tokens"
    )
    JWT_ALLOWED_AUDIENCES: List[str] = Field(
        default_factory=list,
        description="List of allowed audience values for token validation",
    )

    # Middleware configuration
    MIDDLEWARE_CORS_OPTIONS: dict = Field(
        default_factory=lambda: {
            "allow_origins": ["*"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        },
        description="CORS middleware options (passed to CORSMiddleware)",
    )
    RATE_LIMITING_OPTIONS: dict = Field(
        default_factory=lambda: {"max_requests": 60, "window_seconds": 60},
        description="Rate limiting options (max_requests, window_seconds)",
    )
    RATE_LIMITING_BACKEND: str = Field(
        default="memory", description='Rate limiting backend: "memory" or "redis"'
    )

    # Monitoring configuration
    HEALTH_PATH: str = Field(
        default="/health", description="Health check endpoint path"
    )
    HEALTH_INCLUDE_DETAILS: bool = Field(
        default=True, description="Include detailed health check info in response"
    )
    METRICS_PATH: str = Field(
        default="/metrics", description="Prometheus metrics endpoint path"
    )
    METRICS_EXCLUDE_PATHS: List[str] = Field(
        default=["/metrics", "/health"],
        description="List of paths to exclude from metrics collection",
    )

    @field_validator("JWT_AUDIENCE", "JWT_ISSUER", mode="before")
    def set_default_aud_iss(cls, value, info):
        """Set default audience and issuer based on app name if not provided."""
        if value is None:
            # Use the app name as default audience/issuer if not set
            app_name = info.data.get("APP_NAME", "FastCore")
            return app_name.lower()
        return value

    @field_validator("JWT_ALLOWED_AUDIENCES", mode="before")
    def set_default_allowed_audiences(cls, value, info):
        """Set the default allowed audiences list if not provided."""
        if not value:
            # Include the default audience in the allowed list
            audience = info.data.get("JWT_AUDIENCE")
            if audience:
                return [audience]
        return value

    @field_validator("JWT_SECRET_KEY", mode="before")
    def generate_jwt_secret_if_empty(cls, value, info):
        """
        Generate a secure random JWT secret key if not provided.

        In development, this will generate a random key for convenience.
        In production, it's strongly recommended to set this explicitly.
        """
        if not value:
            # Generate a secure random key if not provided
            is_debug = info.data.get("DEBUG", False)
            if is_debug:
                # In debug mode, generate a random key but warn
                new_key = secrets.token_hex(32)
                # logger.warning(
                #     "WARNING: Using auto-generated JWT_SECRET_KEY. "
                #     "This is acceptable for development but not for production."
                # )
                # print(
                #     "WARNING: Using auto-generated JWT_SECRET_KEY. "
                #     "This is acceptable for development but not for production."
                # )
                return new_key
            else:
                # In production, require explicit setting
                raise ValueError(
                    "JWT_SECRET_KEY must be explicitly set in production. "
                    "Generate a secure key with: python -c 'import secrets; print(secrets.token_hex(32))'"
                )
        return value

    @field_validator("DATABASE_URL", mode="before")
    def validate_database_url(cls, value):
        """
        Ensure DATABASE_URL uses asyncpg for PostgreSQL connections.
        """
        if (
            value
            and value.startswith("postgresql://")
            and not value.startswith("postgresql+asyncpg://")
        ):
            raise ValueError(
                "DATABASE_URL must start with 'postgresql+asyncpg://' for asyncpg driver. "
                "You provided a URL starting with 'postgresql://', which will cause psycopg2 errors. "
                "Please update your DATABASE_URL to use the correct format."
            )
        return value

    @field_validator("CACHE_URL", mode="before")
    def validate_cache_url(cls, value):
        """
        Ensure CACHE_URL uses redis:// or rediss:// scheme.
        """
        if value and not (
            value.startswith("redis://") or value.startswith("rediss://")
        ):
            raise ValueError(
                "CACHE_URL must start with 'redis://' or 'rediss://'. "
                f"You provided: {value}"
            )
        return value

    model_config = ConfigDict(env_file=".env", case_sensitive=True)
