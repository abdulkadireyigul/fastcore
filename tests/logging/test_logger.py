"""
Tests for logging functionality.

This module contains tests for the logging module's core functionality,
including configuration, formatting, and handler behavior.
"""

import json
import logging
import os
import tempfile
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastcore.config.app import LoggingSettings
from fastcore.config.base import Environment
from fastcore.factory import create_app
from fastcore.logging import (
    BufferedHandler,
    ColorFormatter,
    JsonFormatter,
    LogLevel,
    configure_logging,
    get_logger,
)
from fastcore.logging.logger import _loggers  # Import the logger cache
from fastcore.logging.logger import get_default_log_format, get_default_log_level


class TestLogLevel:
    """Tests for the LogLevel enum."""

    def test_values(self):
        """Test that enum values are correct."""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"

    def test_from_string(self):
        """Test conversion from string to logging level constant."""
        assert LogLevel.from_string(LogLevel.DEBUG) == logging.DEBUG
        assert LogLevel.from_string(LogLevel.INFO) == logging.INFO
        assert LogLevel.from_string(LogLevel.WARNING) == logging.WARNING
        assert LogLevel.from_string(LogLevel.ERROR) == logging.ERROR
        assert LogLevel.from_string(LogLevel.CRITICAL) == logging.CRITICAL
        # Test default case
        assert LogLevel.from_string("INVALID") == logging.INFO

    def test_log_level_from_string(self):
        """Additional test for LogLevel.from_string."""
        assert LogLevel.from_string("DEBUG") == logging.DEBUG
        assert LogLevel.from_string("INFO") == logging.INFO
        assert LogLevel.from_string("WARNING") == logging.WARNING
        assert LogLevel.from_string("ERROR") == logging.ERROR
        assert LogLevel.from_string("CRITICAL") == logging.CRITICAL
        assert LogLevel.from_string("INVALID") == logging.INFO  # Default fallback


class TestConfigureLogging:
    """Tests for the configure_logging function."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Remove all handlers from the root logger
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def teardown_method(self):
        """Clean up after each test."""
        # Remove all handlers from the root logger
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    @patch("fastcore.logging.logger.AppSettings")
    def test_configure_with_default_settings(self, mock_app_settings):
        """Test logging configuration with default settings."""
        # Mock the settings that would be used
        mock_logging_settings = MagicMock()
        mock_logging_settings.LEVEL = "INFO"
        mock_logging_settings.FORMAT = "%(levelname)s: %(message)s"
        mock_logging_settings.FILE_PATH = None

        mock_app_settings.load.return_value.LOGGING = mock_logging_settings

        # Configure logging
        configure_logging()

        # Verify the root logger was configured correctly
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)

    def test_configure_with_explicit_settings(self):
        """Test logging configuration with explicitly provided settings."""
        # Create custom settings
        settings = LoggingSettings()
        settings.LEVEL = "DEBUG"
        settings.FORMAT = "TEST: %(message)s"

        # Configure logging with explicit settings
        configure_logging(settings=settings)

        # Verify the root logger was configured correctly
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)
        assert root_logger.handlers[0].formatter._fmt == "TEST: %(message)s"

    def test_configure_with_file_output(self):
        """Test logging configuration with file output."""
        # Create a temporary file for logging
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            log_path = tmp.name

        try:
            # Configure logging with file output
            configure_logging(log_file=log_path, log_level="INFO")

            # Verify the root logger has two handlers (console and file)
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) == 2

            # One should be a StreamHandler, the other a FileHandler
            handlers_by_type = {type(h).__name__: h for h in root_logger.handlers}
            assert "StreamHandler" in handlers_by_type
            assert "FileHandler" in handlers_by_type

            # Log a test message
            logger = get_logger("test")
            logger.info("Test log message to file")

            # Close all handlers before accessing the file to avoid permission issues
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)

            # Verify the message was written to the file
            with open(log_path, "r") as file:
                content = file.read()
                assert "Test log message to file" in content

        finally:
            # Clean up the temporary file
            if os.path.exists(log_path):
                try:
                    os.unlink(log_path)
                except PermissionError:
                    # On Windows, sometimes file handles aren't immediately released
                    # We can just log this rather than failing the test
                    print(f"Warning: Could not delete temporary file {log_path}")

    @patch("fastcore.logging.logger.logging")
    def test_configure_logging(self, mock_logging):
        """Additional test for configure_logging."""
        mock_env = Environment.DEVELOPMENT
        mock_settings = MagicMock()
        mock_settings.LEVEL = "DEBUG"
        mock_settings.FORMAT = "%(message)s"
        mock_settings.FILE_PATH = None

        # Use the actual logging.DEBUG value instead of a mocked one
        with patch("fastcore.logging.logger.logging.DEBUG", logging.DEBUG):
            configure_logging(settings=mock_settings, env=mock_env)

        mock_logging.getLogger.assert_called()
        root_logger = mock_logging.getLogger()
        root_logger.setLevel.assert_called_with(logging.DEBUG)


class TestGetLogger:
    """Tests for the get_logger function."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Mock configure_logging to avoid side effects
        self.patcher = patch("fastcore.logging.logger.configure_logging")
        self.patcher.start()

        # Clear the logger cache
        from fastcore.logging import logger

        logger._loggers = {}

    def teardown_method(self):
        """Clean up after each test."""
        self.patcher.stop()

    def test_get_logger_new(self):
        """Test getting a new logger."""
        logger = get_logger("test_module")
        assert logger.name == "test_module"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_cached(self):
        """Test that loggers are cached and reused."""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        assert logger1 is logger2  # Should be the same instance

    @patch("fastcore.logging.logger._loggers", new_callable=dict)
    def test_get_logger(self, mock_loggers):
        """Additional test for get_logger."""
        logger_name = "test_logger"
        logger = get_logger(logger_name)

        # Ensure the logger is added to the mocked _loggers dictionary
        assert logger_name in mock_loggers
        assert mock_loggers[logger_name] is logger

        # Ensure cached logger is returned
        cached_logger = get_logger(logger_name)
        assert cached_logger is logger


class TestJsonFormatter:
    """Tests for the JsonFormatter class."""

    def test_format_basic(self):
        """Test basic JSON formatting."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert "timestamp" in parsed
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"
        assert parsed["message"] == "Test message"

    def test_format_with_extra(self):
        """Test JSON formatting with extra fields."""
        formatter = JsonFormatter(extra_fields={"app": "test_app", "version": "1.0"})
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add a custom attribute to the record
        record.user_id = "123"

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["app"] == "test_app"
        assert parsed["version"] == "1.0"
        assert parsed["user_id"] == "123"


class TestColorFormatter:
    """Tests for the ColorFormatter class."""

    def test_format_with_color(self):
        """Test that color codes are added to level names."""
        formatter = ColorFormatter("%(levelname)s: %(message)s")
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test_file.py",
            lineno=42,
            msg="Test error message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # Check that the color code for ERROR is in the formatted string
        assert "\033[31m" in formatted  # Red color for ERROR
        assert "\033[0m" in formatted  # Reset color


class TestBufferedHandler:
    """Tests for the BufferedHandler class."""

    def test_emit_and_get_records(self):
        """Test storing and retrieving log records."""
        handler = BufferedHandler(capacity=5)

        # Create and emit 3 records
        for i in range(3):
            record = logging.LogRecord(
                name="test_logger",
                level=logging.INFO,
                pathname="test_file.py",
                lineno=42,
                msg=f"Message {i}",
                args=(),
                exc_info=None,
            )
            handler.emit(record)

        # Check that all records are stored
        records = handler.get_records()
        assert len(records) == 3
        assert records[0].getMessage() == "Message 2"  # Newest first
        assert records[2].getMessage() == "Message 0"  # Oldest last

    def test_capacity_limit(self):
        """Test that the buffer respects capacity limits."""
        handler = BufferedHandler(capacity=3)

        # Create and emit 5 records
        for i in range(5):
            record = logging.LogRecord(
                name="test_logger",
                level=logging.INFO,
                pathname="test_file.py",
                lineno=42,
                msg=f"Message {i}",
                args=(),
                exc_info=None,
            )
            handler.emit(record)

        # Check that only the most recent 3 records are stored
        records = handler.get_records()
        assert len(records) == 3
        assert records[0].getMessage() == "Message 4"
        assert records[2].getMessage() == "Message 2"

    def test_clear(self):
        """Test clearing the buffer."""
        handler = BufferedHandler()

        # Create and emit a record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        handler.emit(record)

        # Check that the record is stored
        assert len(handler.get_records()) == 1

        # Clear the buffer and check that it's empty
        handler.clear()
        assert len(handler.get_records()) == 0


class TestAppFactoryIntegration:
    """Tests for logging integration in the app factory."""

    @patch("fastcore.factory.configure_logging")
    def test_factory_configures_logging(self, mock_configure_logging):
        """Test that the app factory configures logging."""
        app = create_app(env=Environment.DEVELOPMENT, enable_logging=True)

        # Verify that configure_logging was called
        mock_configure_logging.assert_called_once()

    @patch("fastcore.factory.configure_logging")
    def test_factory_disables_logging(self, mock_configure_logging):
        """Test that the app factory can disable logging configuration."""
        app = create_app(env=Environment.DEVELOPMENT, enable_logging=False)

        # Verify that configure_logging was not called
        mock_configure_logging.assert_not_called()

    def test_logging_in_request_handling(self):
        """Test that logging works during request handling."""
        # Create an app with a simple endpoint that logs a message
        app = FastAPI()

        test_logger = get_logger("test")

        @app.get("/test")
        def test_endpoint():
            test_logger.info("Test endpoint called")
            return {"message": "Hello, world!"}

        # Use a StringIO as a log sink to capture log messages
        log_output = StringIO()
        handler = logging.StreamHandler(log_output)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

        # Add the handler to our test logger
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.INFO)

        # Make a request to the test endpoint
        client = TestClient(app)
        response = client.get("/test")

        # Check that the log message was recorded
        log_output.seek(0)
        log_content = log_output.read()
        assert "INFO: Test endpoint called" in log_content

        # Clean up
        test_logger.removeHandler(handler)


class TestDefaultLogSettings:
    """Tests for default log settings."""

    def test_get_default_log_level(self):
        """Test default log level based on environment."""
        assert get_default_log_level(Environment.DEVELOPMENT) == LogLevel.DEBUG
        assert get_default_log_level(Environment.TESTING) == LogLevel.DEBUG
        assert get_default_log_level(Environment.STAGING) == LogLevel.INFO
        assert get_default_log_level(Environment.PRODUCTION) == LogLevel.WARNING

    def test_get_default_log_format(self):
        """Test default log format based on environment."""
        dev_format = get_default_log_format(Environment.DEVELOPMENT)
        prod_format = get_default_log_format(Environment.PRODUCTION)

        assert "%(asctime)s" in dev_format
        assert "%(levelname)-8s" in dev_format
        assert "%(name)s:%(lineno)d" in dev_format

        assert "%(asctime)s" in prod_format
        assert "%(levelname)-8s" in prod_format
        assert "%(name)s" in prod_format
        assert ":%(lineno)d" not in prod_format
