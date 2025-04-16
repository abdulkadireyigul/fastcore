"""
Custom formatters for logging.

This module provides specialized formatters for different logging scenarios,
such as JSON formatting for structured logging or colored console output.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional


class JsonFormatter(logging.Formatter):
    """
    Format log records as JSON strings.

    This formatter is useful for structured logging where logs will be
    processed by tools like ELK stack or other log aggregation systems.
    """

    def __init__(
        self,
        include_timestamp: bool = True,
        include_level: bool = True,
        include_name: bool = True,
        extra_fields: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the JSON formatter.

        Args:
            include_timestamp: Whether to include a timestamp field
            include_level: Whether to include the log level
            include_name: Whether to include the logger name
            extra_fields: Additional fields to include in every log record
        """
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_name = include_name
        self.extra_fields = extra_fields or {}

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.

        Args:
            record: The log record to format

        Returns:
            A JSON-formatted string representation of the log record
        """
        log_data: Dict[str, Any] = {}

        # Add standard fields
        if self.include_timestamp:
            log_data["timestamp"] = datetime.fromtimestamp(record.created).isoformat()

        if self.include_level:
            log_data["level"] = record.levelname

        if self.include_name:
            log_data["logger"] = record.name

        # Add the actual log message
        log_data["message"] = record.getMessage()

        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields from record attributes
        for key, value in record.__dict__.items():
            if key not in [
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "id",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            ]:
                log_data[key] = value

        # Add any extra fields specified in the constructor
        log_data.update(self.extra_fields)

        # Return the JSON-formatted string
        return json.dumps(log_data)


class ColorFormatter(logging.Formatter):
    """
    Format log records with ANSI color codes for console output.

    This formatter adds color to log messages based on their level,
    making it easier to identify different types of logs in the console.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[41m\033[37m",  # White on Red background
        "RESET": "\033[0m",  # Reset
    }

    def __init__(self, fmt: Optional[str] = None):
        """
        Initialize the color formatter.

        Args:
            fmt: The format string to use for formatting log records
        """
        super().__init__(fmt)

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with color.

        Args:
            record: The log record to format

        Returns:
            A color-coded string representation of the log record
        """
        # Save the original levelname
        levelname = record.levelname

        # Add color to the levelname
        color = self.COLORS.get(levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        record.levelname = f"{color}{levelname}{reset}"

        # Format the record with the colored levelname
        result = super().format(record)

        # Restore the original levelname
        record.levelname = levelname

        return result
