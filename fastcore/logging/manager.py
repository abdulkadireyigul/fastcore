"""
Basic logging configuration for FastAPI applications.

This module provides a simple and consistent logging setup across different environments.
"""

import logging
import sys
from typing import Optional

from fastcore_v2.config.base import BaseAppSettings

from .formatters import JsonFormatter


def setup_logger(
    name: str,
    level: str = "INFO",
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    debug: bool = False,
    json_format: bool = False,
) -> logging.Logger:
    """
    Create and configure a logger instance.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Log message format (ignored if json_format=True)
        debug: If True, sets level to DEBUG regardless of level parameter
        json_format: If True, outputs logs in JSON format

    Returns:
        Configured logger instance
    """
    # Convert string level to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)
    if debug:
        log_level = logging.DEBUG

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = JsonFormatter() if json_format else logging.Formatter(format)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    return logger


def get_logger(
    name: str, settings: Optional[BaseAppSettings] = None, json_format: bool = False
) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (usually __name__)
        settings: Optional application settings
        json_format: If True, outputs logs in JSON format

    Returns:
        Configured logger instance
    """
    # Safely check debug mode
    debug = False
    if settings and hasattr(settings, "DEBUG"):
        debug = bool(settings.DEBUG)

    return setup_logger(name, debug=debug, json_format=json_format)
