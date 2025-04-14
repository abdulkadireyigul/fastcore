"""
Basic logging configuration for FastAPI applications.

This module provides a simple and consistent logging setup across different environments.
"""

import logging
import sys
from typing import Optional

from fastcore_v2.config.base import BaseAppSettings


def setup_logger(
    name: str,
    level: str = "INFO",
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    debug: bool = False,
) -> logging.Logger:
    """
    Create and configure a logger instance.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Log message format
        debug: If True, sets level to DEBUG regardless of level parameter

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

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter(format)
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str, settings: Optional[BaseAppSettings] = None) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (usually __name__)
        settings: Optional application settings

    Returns:
        Configured logger instance
    """
    debug = settings.DEBUG if settings else False
    return setup_logger(name, debug=debug)
