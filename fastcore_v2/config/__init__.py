"""
Configuration management for FastAPI applications.

This module provides a simple, environment-aware configuration system
that supports development, testing, and production environments.
"""

from fastcore_v2.config.base import BaseAppSettings
from fastcore_v2.config.development import DevelopmentSettings
from fastcore_v2.config.production import ProductionSettings
from fastcore_v2.config.settings import get_settings, settings
from fastcore_v2.config.testing import TestingSettings

__all__ = [
    "BaseAppSettings",
    "get_settings",
    "settings",
    "DevelopmentSettings",
    "ProductionSettings",
    "TestingSettings",
]
