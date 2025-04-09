"""
Custom handlers for logging.

This module provides specialized log handlers for different logging scenarios,
such as rotating file logs or buffered logging for web applications.
"""

import logging
import os
import threading
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Any, Dict, List, Optional


class BufferedHandler(logging.Handler):
    """
    A handler that stores log records in memory.

    This is useful for web applications where you might want to include
    recent log messages in error responses or debugging endpoints.
    """

    def __init__(
        self,
        capacity: int = 1000,
        level: int = logging.NOTSET,
    ):
        """
        Initialize the buffered handler.

        Args:
            capacity: Maximum number of log records to store
            level: Minimum log level to handle
        """
        super().__init__(level)
        self.capacity = capacity
        self.buffer: List[logging.LogRecord] = []
        self.lock = threading.RLock()

    def emit(self, record: logging.LogRecord) -> None:
        """
        Store the log record in the buffer.

        Args:
            record: The log record to store
        """
        with self.lock:
            self.buffer.append(record)

            # Trim buffer if it exceeds capacity
            if len(self.buffer) > self.capacity:
                self.buffer = self.buffer[-self.capacity :]

    def get_records(self, limit: Optional[int] = None) -> List[logging.LogRecord]:
        """
        Get recent log records from the buffer.

        Args:
            limit: Optional maximum number of records to return

        Returns:
            A list of recent log records, newest first
        """
        with self.lock:
            if limit is None or limit >= len(self.buffer):
                return list(reversed(self.buffer))
            else:
                return list(reversed(self.buffer))[:limit]

    def clear(self) -> None:
        """Clear all log records from the buffer."""
        with self.lock:
            self.buffer = []


class SafeRotatingFileHandler(RotatingFileHandler):
    """
    A rotating file handler that won't fail if the log directory doesn't exist.

    This handler automatically creates the log directory if it doesn't exist,
    making it more robust for applications running in various environments.
    """

    def __init__(
        self,
        filename: str,
        mode: str = "a",
        maxBytes: int = 0,
        backupCount: int = 0,
        encoding: Optional[str] = None,
        delay: bool = False,
    ):
        """
        Initialize the safe rotating file handler.

        Args:
            filename: Path to the log file
            mode: File opening mode
            maxBytes: Maximum size of the log file before rotation
            backupCount: Number of backup files to keep
            encoding: Character encoding to use
            delay: Whether to delay opening the file until first log
        """
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(filename)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)


class RequestContextHandler(logging.Handler):
    """
    A handler that adds request context to log records.

    This handler is useful for web applications where you want to include
    information about the current request (like request ID, user ID, etc.)
    in all log messages emitted during request processing.
    """

    _context: threading.local = threading.local()

    def __init__(self, level: int = logging.NOTSET):
        """
        Initialize the request context handler.

        Args:
            level: Minimum log level to handle
        """
        super().__init__(level)

    @classmethod
    def set_context(cls, **context: Any) -> None:
        """
        Set context values for the current thread.

        Args:
            **context: Key-value pairs to add to the context

        Example:
            ```python
            @app.middleware("http")
            async def add_request_id(request, call_next):
                request_id = str(uuid.uuid4())
                RequestContextHandler.set_context(request_id=request_id)
                return await call_next(request)
            ```
        """
        if not hasattr(cls._context, "data"):
            cls._context.data = {}
        cls._context.data.update(context)

    @classmethod
    def get_context(cls) -> Dict[str, Any]:
        """
        Get the current thread's context.

        Returns:
            A dictionary of context values
        """
        if not hasattr(cls._context, "data"):
            cls._context.data = {}
        return cls._context.data

    @classmethod
    def clear_context(cls) -> None:
        """Clear all context values for the current thread."""
        cls._context.data = {}

    def emit(self, record: logging.LogRecord) -> None:
        """
        Add context data to the log record.

        Args:
            record: The log record to modify
        """
        context = self.get_context()
        for key, value in context.items():
            setattr(record, key, value)
