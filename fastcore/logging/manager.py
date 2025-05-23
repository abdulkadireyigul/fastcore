"""
Basic logging configuration for FastAPI 
applications.

This module provides a simple and consistent 
logging setup across different environments.

Limitations:
- Only console (stdout) logging is supported out of the box.
- No file logging, log rotation, or external service integration.
- JSON logs include only timestamp, level, and message by default.
"""

import logging
import sys
from typing import Optional, Union

from fastcore.config.base import BaseAppSettings
from fastcore.logging.formatters import JsonFormatter

Logger = Union[logging.Logger, object]


def setup_logger(
    name: str,
    level: str = "INFO",
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    debug: bool = False,
    json_format: bool = False,
) -> Logger:
    """
    Create and configure a logger instance.

    Only console (stdout) logging is supported. No file logging or log rotation.
    If json_format is True, only timestamp, level, and message are included in the output.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Log message format (ignored if json_format=True)
        debug: If True, sets level to DEBUG regardless of level parameter
        json_format: If True, outputs logs in JSON format (basic fields only)

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
) -> Logger:
    """
    Get a configured logger instance.

    Only console (stdout) logging is supported. No file logging or log rotation.
    If json_format is True, only timestamp, level, and message are included in the output.

    Args:
        name: Logger name (usually __name__)
        settings: Optional application settings
        json_format: If True, outputs logs in JSON format (basic fields only)

    Returns:
        Configured logger instance
    """
    # Safely check debug mode
    debug = False
    if settings and hasattr(settings, "DEBUG"):
        debug = bool(settings.DEBUG)

    return setup_logger(name, debug=debug, json_format=json_format)


def ensure_logger(
    logger: Optional[Logger] = None,
    name: str = None,
    settings: Optional[BaseAppSettings] = None,
    json_format: bool = False,
) -> Logger:
    """
    Ensure a logger instance is available by either using the provided one or creating a new one.

    Only console (stdout) logging is supported. No file logging or log rotation.
    If json_format is True, only timestamp, level, and message are included in the output.

    Args:
        logger: An existing logger instance to use if provided
        name: Module name (usually __name__) for creating a new logger if needed
        settings: Optional application settings
        json_format: If True, outputs logs in JSON format (basic fields only)

    Returns:
        Either the provided logger or a newly created one
    """
    if logger:
        return logger

    if not name:
        raise ValueError("Module name must be provided when logger is not specified")

    return get_logger(name, settings, json_format)
