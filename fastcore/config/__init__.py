"""
Configuration management for FastAPI applications.

This module provides tools for managing application configuration
in a consistent, type-safe, and environment-aware manner.
"""

from fastcore.config.app import (
    APISettings,
    AppSettings,
    CORSSettings,
    DatabaseSettings,
    LoggingSettings,
)
from fastcore.config.base import BaseSettings, Environment

__all__ = [
    "BaseSettings",
    "Environment",
    "AppSettings",
    "APISettings",
    "CORSSettings",
    "DatabaseSettings",
    "LoggingSettings",
]
