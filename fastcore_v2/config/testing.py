"""
Testing environment specific settings.

This module contains settings that are specific to the testing environment,
such as test database configurations and testing-specific flags.
"""

from .base import BaseAppSettings


class TestingSettings(BaseAppSettings):
    """
    Settings class for testing environment.

    Uses in-memory SQLite database and enables debug mode for testing.
    Inherits basic settings from BaseAppSettings.

    Attributes:
        DEBUG: Set to True for detailed test output
        DATABASE_URL: In-memory SQLite connection string for testing
    """

    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./test.db"
