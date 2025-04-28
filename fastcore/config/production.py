"""
Production environment specific settings.

This module contains settings that are specific to the production environment,
such as database configurations and security settings.
"""

from .base import BaseAppSettings


class ProductionSettings(BaseAppSettings):
    """
    Settings class for production environment.

    Disables debug mode and uses production database configuration.
    Inherits basic settings from BaseAppSettings.

    Attributes:
        DEBUG: Always False in production for security
        DATABASE_URL: Connection string for production database
    """

    DEBUG: bool = False
    DATABASE_URL: str = "postgresql://user:pass@host:port/db"
