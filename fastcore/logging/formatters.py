"""
Custom log formatters for FastAPI applications.

This module contains formatters that determine how log records are formatted.
Currently supports JSON formatting for structured logging.

Limitations:
- JSON logs include only timestamp, level, and message by default.
- Extra fields passed to logger (via extra=...) are not included unless you extend the formatter.
"""

import json
import logging
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """
    Format log records as JSON for structured logging.

    This formatter converts log records into JSON format, making them
    suitable for log aggregation services and structured logging.

    Only timestamp, level, and message are included by default.
    To include extra fields, subclass and extend this formatter.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the specified record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string containing the formatted log record
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        return json.dumps(log_data)
