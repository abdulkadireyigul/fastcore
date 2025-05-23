"""
Logging module for FastAPI applications.

This module provides a simple logging interface 
that integrates with application settings.

Limitations:
- Only console (stdout) logging is supported out of the box.
- No file logging, log rotation, or external service integration.
- JSON logs include only timestamp, level, and message by default.
"""

from fastcore.logging.formatters import JsonFormatter
from fastcore.logging.manager import Logger, ensure_logger, get_logger, setup_logger

__all__ = [
    "Logger",
    "get_logger",
    "ensure_logger",
    "setup_logger",
    "JsonFormatter",  # Public API
]
