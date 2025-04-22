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

# Public API exports
from fastcore.factory import configure_app
from fastcore.cache import get_cache
from fastcore.cache.decorators import cache
from fastcore.config import get_settings, BaseAppSettings
from fastcore.errors import AppError, setup_errors
from fastcore.logging import get_logger
from fastcore.schemas import ResponseModel, DataResponse, ErrorResponse
from fastcore.security import get_current_user, authenticate_user