"""
Application settings management module.

This module handles the loading of environment-specific settings
based on the APP_ENV environment variable. It provides a centralized
way to access the correct settings instance for the current environment.
"""

import os

from .development import DevelopmentSettings
from .production import ProductionSettings
from .testing import TestingSettings


def get_settings():
    """
    Get the appropriate settings instance for the current environment.

    The environment is determined by the APP_ENV environment variable.
    If not set, defaults to 'development'.

    Returns:
        BaseAppSettings: An instance of environment-specific settings
    """
    env = os.getenv("APP_ENV", "development")
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    return DevelopmentSettings()


settings = get_settings()
