"""
Logging utilities for FastAPI applications.

This module provides standardized logging setup and utilities
for FastAPI applications, including configurability, formatters,
and specialized handlers for different environments.
"""

from fastcore.logging.formatters import ColorFormatter, JsonFormatter
from fastcore.logging.handlers import (
    BufferedHandler,
    RequestContextHandler,
    SafeRotatingFileHandler,
)
from fastcore.logging.logger import Logger, LogLevel, configure_logging, get_logger

__all__ = [
    # Core logging functionality
    "get_logger",
    "configure_logging",
    "LogLevel",
    "Logger",
    # Formatters
    "ColorFormatter",
    "JsonFormatter",
    # Handlers
    "BufferedHandler",
    "RequestContextHandler",
    "SafeRotatingFileHandler",
]
