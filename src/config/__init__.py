"""
Configuration management for FastAPI applications.

This module provides a simple, environment-aware configuration system
that supports development, testing, and production environments.
"""

from .base import BaseAppSettings
from .settings import get_settings, settings

# from .development import DevelopmentSettings
# from .production import ProductionSettings
# from .testing import TestingSettings

__all__ = [
    "BaseAppSettings",
    "get_settings",
    "settings",
    # "DevelopmentSettings",
    # "ProductionSettings",
    # "TestingSettings",
]
