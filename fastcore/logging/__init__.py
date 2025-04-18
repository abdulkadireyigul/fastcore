"""
Logging module for FastAPI applications.

This module provides a simple logging interface 
that integrates with application settings.
"""

from fastcore.logging.formatters import JsonFormatter
from fastcore.logging.manager import get_logger, setup_logger

__all__ = ["get_logger", "setup_logger", "JsonFormatter"]
