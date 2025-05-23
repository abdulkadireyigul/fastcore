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

# Application
APP_NAME="FastCore"
APP_ENV="development"  # Options: development, testing, production
VERSION="1.0.0"
DEBUG=true

# Cache configuration
CACHE_URL="redis://localhost:6379/0"
CACHE_DEFAULT_TTL=300
CACHE_KEY_PREFIX="fastcore:"

# Database configuration
DATABASE_URL="postgresql+asyncpg://<username>:<password>@<host>:<port>/<database_name>"
ALEMBIC_DATABASE_URL="postgresql://<username>:<password>@<host>:<port>/<database_name>"
DB_ECHO=false
DB_POOL_SIZE=5

# Security configuration
JWT_SECRET_KEY="your-secret-key-at-least-32-characters-long"
JWT_ALGORITHM="HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_AUDIENCE="fastcore"
JWT_ISSUER="fastcore"

# Middleware configuration
MIDDLEWARE_CORS_OPTIONS='{"allow_origins":["http://localhost:3000"],"allow_credentials":true,"allow_methods":["*"],"allow_headers":["*"]}'
RATE_LIMITING_OPTIONS='{"max_requests":60,"window_seconds":60}'
RATE_LIMITING_BACKEND="redis"

# Monitoring configuration
HEALTH_PATH="/health"
HEALTH_INCLUDE_DETAILS=true
METRICS_PATH="/metrics"
METRICS_EXCLUDE_PATHS='["/metrics", "/health"]'

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
