"""
FastCore - Core utilities for FastAPI applications with minimal boilerplate.

This package provides a collection of utilities and modules for building
robust FastAPI applications with a focus on clean architecture, minimal
boilerplate, and best practices.

Usage:
    from fastapi import FastAPI
    from fastcore.factory import configure_app
    
    app = FastAPI()
    configure_app(app)
"""

__version__ = "0.1.0"
__api_version__ = "v1"
__author__ = "Abdulkadir Eyigül"
__license__ = "MIT"
__min_python_version__ = "3.8"
__min_fastapi_version__ = "0.100.0"

# Version compatibility information
# The tuple format is (major, minor, patch)
__version_info__ = (0, 1, 0)
__api_version_info__ = (1, 0, 0)

# Public API exports
from src.cache import get_cache
from src.cache.decorators import cache
from src.config import BaseAppSettings, get_settings
from src.errors import AppError, setup_errors
from src.factory import configure_app
from src.logging import get_logger
from src.schemas import DataResponse, ErrorResponse
