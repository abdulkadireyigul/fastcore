"""
Core logging functionality for FastAPI applications.

This module provides logging utilities that integrate with the application's
configuration system and provide consistent logging behavior across environments.
"""

import logging
import os
import sys
from enum import Enum
from typing import Any, Dict, Optional, Union

from fastcore.config.app import AppSettings, LoggingSettings

# Type alias for Python's standard logger
Logger = logging.Logger

# Cache for loggers to avoid creating duplicates
_loggers: Dict[str, Logger] = {}


class LogLevel(str, Enum):
    """
    Enum for standard logging levels.

    This provides a type-safe way to specify log levels in code and configuration.
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_string(cls, level: str) -> int:
        """
        Convert a string log level to the corresponding logging module constant.

        Args:
            level: The string representation of the log level

        Returns:
            The numeric log level from the logging module

        Example:
            ```python
            level = LogLevel.from_string("INFO")
            assert level == logging.INFO
            ```
        """
        level_map = {
            cls.DEBUG: logging.DEBUG,
            cls.INFO: logging.INFO,
            cls.WARNING: logging.WARNING,
            cls.ERROR: logging.ERROR,
            cls.CRITICAL: logging.CRITICAL,
        }
        return level_map.get(level, logging.INFO)


def configure_logging(
    settings: Optional[LoggingSettings] = None,
    log_file: Optional[str] = None,
    log_level: Optional[Union[str, LogLevel]] = None,
    log_format: Optional[str] = None,
) -> None:
    """
    Configure the Python logging system for FastAPI applications.

    This function sets up both console and file logging (if a file path is provided).

    Args:
        settings: Optional logging settings to use instead of deriving from app settings
        log_file: Optional path to a log file, overrides settings if provided
        log_level: Optional log level, overrides settings if provided
        log_format: Optional log format string, overrides settings if provided

    Example:
        ```python
        # Configure using app settings
        configure_logging()

        # Configure with custom parameters
        configure_logging(log_level="DEBUG", log_file="/path/to/app.log")
        ```
    """
    # Get settings if not provided
    if settings is None:
        app_settings = AppSettings.load()
        settings = app_settings.LOGGING

    # Get log level
    level_str = log_level or settings.LEVEL
    if isinstance(level_str, LogLevel):
        level = LogLevel.from_string(level_str)
    else:
        level = LogLevel.from_string(level_str)

    # Get log format
    format_str = log_format or settings.FORMAT

    # Get log file path
    file_path = log_file or settings.FILE_PATH

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter(format_str)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)

    # Add file handler if a file path is provided
    if file_path:
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> Logger:
    """
    Get a logger with the given name.

    This function returns a cached logger if it exists, or creates a new one.

    Args:
        name: The name of the logger, typically the module name

    Returns:
        A configured logger instance

    Example:
        ```python
        # Get a logger for the current module
        logger = get_logger(__name__)

        # Log a message
        logger.info("Application started")
        ```
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    _loggers[name] = logger

    return logger
