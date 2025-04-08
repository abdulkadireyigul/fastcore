"""
FastAPI application specific configuration classes.

This module provides pre-configured settings classes for common
FastAPI application needs such as CORS, database connections, etc.
"""

from typing import List, Optional, Union

from pydantic import AnyHttpUrl, BaseSettings, PostgresDsn, validator

from core.config.base import BaseSettings as FastCoreBaseSettings
from core.config.base import Environment


class LoggingSettings(FastCoreBaseSettings):
    """Logging configuration settings."""

    LEVEL: str = "INFO"
    FORMAT: str = "%(levelname)s:     %(message)s"
    FILE_PATH: Optional[str] = None


class CORSSettings(FastCoreBaseSettings):
    """CORS configuration settings."""

    ALLOW_ORIGINS: List[str] = ["*"]
    ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    ALLOW_HEADERS: List[str] = ["*"]
    ALLOW_CREDENTIALS: bool = False


class DatabaseSettings(FastCoreBaseSettings):
    """Database connection settings."""

    DRIVER: str = "postgresql"
    USER: str
    PASSWORD: str
    HOST: str
    PORT: str
    NAME: str
    POOL_SIZE: int = 5

    class Config:
        env_prefix = "DB_"

    @property
    def URL(self) -> str:
        """Construct the database URL."""
        return f"{self.DRIVER}://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.NAME}"


class APISettings(FastCoreBaseSettings):
    """API specific settings."""

    TITLE: str = "FastAPI Application"
    DESCRIPTION: str = "FastAPI application with FastCore library"
    VERSION: str = "0.1.0"
    PREFIX: str = "/api"
    DEBUG: bool = False


class AppSettings(FastCoreBaseSettings):
    """Main application settings that combines all other settings."""

    ENV: Environment = Environment.DEVELOPMENT
    API: APISettings = APISettings()
    CORS: CORSSettings = CORSSettings()
    DB: Optional[DatabaseSettings] = None
    LOGGING: LoggingSettings = LoggingSettings()

    # Additional application-specific settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @classmethod
    def load(
        cls, env: Union[Environment, str] = Environment.DEVELOPMENT
    ) -> "AppSettings":
        """
        Load application settings for the specified environment.

        Args:
            env: The environment to load configuration for

        Returns:
            AppSettings instance with appropriate values for the environment
        """
        if isinstance(env, str):
            env = Environment(env)

        return cls.from_env(env)
