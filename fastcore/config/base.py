"""
Base configuration module for FastAPI applications.

This module provides the base settings class that other settings classes inherit from.
It handles basic application configuration like app name, debug mode, and version.
"""

from pydantic import Field
from pydantic_settings import BaseSettings  # type: ignore


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
        JWT_ALGORITHM: Algorithm used for JWT signing
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES: Minutes until JWT access tokens expire
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
    DATABASE_URL: str = Field(default="", description="Database connection URL")
    DB_ECHO: bool = Field(default=False, description="Enable SQL query logging (echo)")
    DB_POOL_SIZE: int = Field(
        default=5, description="Connection pool size for the database"
    )

    # Security configuration
    JWT_SECRET_KEY: str = Field(
        default="insecure-jwt-secret-key-replace-in-production",
        description="Secret key for JWT token signing",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256", description="Algorithm used for JWT signing"
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Minutes until JWT access tokens expire"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True
