"""
Development environment specific settings.

This module contains settings that are specific to the development environment,
such as debug flags and development database configurations.
"""

from .base import BaseAppSettings


class DevelopmentSettings(BaseAppSettings):
    """
    Settings class for development environment.

    Enables debug mode and uses a local SQLite database by default.
    Inherits basic settings from BaseAppSettings.

    Attributes:
        DEBUG: Always True in development
        DATABASE_URL: Path to development database
    """

    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./dev.db"
