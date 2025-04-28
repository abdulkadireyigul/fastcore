"""
Configuration module for FastCore.

This module provides:
- BaseAppSettings: The base class for application settings, supporting environment variable loading.
- Environment-specific settings (development, testing, production).
- get_settings: Factory for loading the correct settings class based on APP_ENV.

Usage:
- Import and use BaseAppSettings or get_settings in your FastAPI app or library.
- See the example environment variables below for required and optional configuration.

Example environment variables (to be placed in your consuming project's .env or environment):

APP_NAME=FastCore
DEBUG=True
DATABASE_URL=sqlite:///:memory:
JWT_SECRET_KEY=changeme
CACHE_URL=redis://localhost:6379/0
CACHE_DEFAULT_TTL=300
CACHE_KEY_PREFIX=fastcore:
APP_ENV=development
JWT_AUDIENCE=fastcore
JWT_ISSUER=fastcore
JWT_ALLOWED_AUDIENCES=fastcore
HEALTH_PATH=/health
HEALTH_INCLUDE_DETAILS=True
METRICS_PATH=/metrics
METRICS_EXCLUDE_PATHS=/metrics,/health
RATE_LIMITING_BACKEND=memory
RATE_LIMITING_OPTIONS={"max_requests":60,"window_seconds":60}

For a full example, see the env.example file in your main FastAPI project root.
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
