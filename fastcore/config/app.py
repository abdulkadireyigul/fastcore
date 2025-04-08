"""
FastAPI application specific configuration classes.

This module provides pre-configured settings classes for common
FastAPI application needs such as CORS, database connections, etc.

Examples:
    ```python
    # Load application settings for development environment
    from fastcore.config.app import AppSettings, Environment
    
    settings = AppSettings.load(Environment.DEVELOPMENT)
    app = FastAPI(
        title=settings.API.TITLE,
        description=settings.API.DESCRIPTION,
        version=settings.API.VERSION,
    )
    ```
"""

from typing import List, Optional, Union

from fastcore.config.base import BaseSettings as FastCoreBaseSettings
from fastcore.config.base import Environment


class LoggingSettings(FastCoreBaseSettings):
    """
    Logging configuration settings.

    Attributes:
        LEVEL: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        FORMAT: The format string for log messages
        FILE_PATH: Optional path to a log file
    """

    LEVEL: str = "INFO"
    FORMAT: str = "%(levelname)s:     %(message)s"
    FILE_PATH: Optional[str] = None


class CORSSettings(FastCoreBaseSettings):
    """
    CORS configuration settings for API access control.

    Attributes:
        ALLOW_ORIGINS: List of origins that are allowed to make requests
        ALLOW_METHODS: HTTP methods that are allowed in CORS requests
        ALLOW_HEADERS: HTTP headers that are allowed in CORS requests
        ALLOW_CREDENTIALS: Whether to allow credentials (cookies, auth headers)
    """

    ALLOW_ORIGINS: List[str] = ["*"]
    ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    ALLOW_HEADERS: List[str] = ["*"]
    ALLOW_CREDENTIALS: bool = False


class DatabaseSettings(FastCoreBaseSettings):
    """
    Database connection settings.

    Attributes:
        DRIVER: Database driver (e.g., postgresql, mysql)
        USER: Database username
        PASSWORD: Database password
        HOST: Database host address
        PORT: Database port
        NAME: Database name
        POOL_SIZE: Connection pool size

    Properties:
        URL: Constructed database URL string based on individual settings
    """

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
        """
        Construct the database URL from components.

        Returns:
            A connection string URL for database access
        """
        return f"{self.DRIVER}://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.NAME}"


class APISettings(FastCoreBaseSettings):
    """
    API specific settings.

    Attributes:
        TITLE: API title displayed in OpenAPI documentation
        DESCRIPTION: API description displayed in OpenAPI documentation
        VERSION: API version string
        PREFIX: URL prefix for all API endpoints
        DEBUG: Enable debug mode for additional logging and details
    """

    TITLE: str = "FastAPI Application"
    DESCRIPTION: str = "FastAPI application with FastCore library"
    VERSION: str = "0.1.0"
    PREFIX: str = "/api"
    DEBUG: bool = False


class AppSettings(FastCoreBaseSettings):
    """
    Main application settings that combines all other settings.

    This is the primary settings class that should be used by applications.
    It aggregates all sub-settings into a single configuration object.

    Attributes:
        ENV: Current environment (development, testing, staging, production)
        API: API-related settings
        CORS: CORS configuration settings
        DB: Database connection settings (optional)
        LOGGING: Logging configuration
        SECRET_KEY: Application secret key for security features
        ALGORITHM: Hash algorithm for token generation (default: HS256)
        ACCESS_TOKEN_EXPIRE_MINUTES: Token expiration time in minutes

    Example:
        ```python
        settings = AppSettings.load(Environment.DEVELOPMENT)
        print(f"Running in {settings.ENV} mode")
        print(f"API URL prefix: {settings.API.PREFIX}")
        ```
    """

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
                 (development, testing, staging, production)

        Returns:
            AppSettings instance with appropriate values for the environment

        Example:
            ```python
            # Load production settings
            prod_settings = AppSettings.load(Environment.PRODUCTION)

            # Load from string
            dev_settings = AppSettings.load("development")
            ```
        """
        if isinstance(env, str):
            env = Environment(env)

        return cls.from_env(env)
