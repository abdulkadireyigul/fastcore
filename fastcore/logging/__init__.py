"""
Logging module for FastAPI applications.

This module provides a simple logging interface 
that integrates with application settings.
"""

from .formatters import JsonFormatter
from .manager import get_logger, setup_logger

__all__ = ["get_logger", "setup_logger", "JsonFormatter"]
